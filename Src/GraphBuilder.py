import json
import os
import pickle
import re

import networkx as nx
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

Model = "gemini-3.6-flash"

SystemPrompt = """You are a business analyst designing a concept glossary for a BI Copilot.

You will be given a database schema catalog as a flat text summary, one line per table
in the form "Schema.Table: col1, col2, ...".

CRITICAL NAMING RULE: concept names must be natural business language that a
non-technical person would actually say out loud - NOT the column name reworded.

WRONG (do not do this): "Sales Line Total" for the LineTotal column, "Sales Tax Amount" for TaxAmt.
These just restate the column name in words - they don't help at all, because the whole point
is bridging the gap between business language and schema language.

RIGHT: "Revenue" for LineTotal, "Sales Tax" for TaxAmt, "Order Value" for TotalDue.
Use the term a business user would actually type into a search box.

WORKED EXAMPLE - multi-anchor concept:
"Profit" is a concept that cannot come from a single column, because no single column in
this schema stores profit directly. Profit = revenue earned minus the cost of making the
product sold. That means it needs TWO anchors from two different tables:
  1. A revenue anchor: Sales.SalesOrderDetail.LineTotal (money earned per line item)
  2. A cost anchor: Production.Product.StandardCost (cost to produce that item)
Look for this same pattern elsewhere in the schema: any concept describing a margin,
a net amount, a rate of return, or a comparison between two figures likely needs
multiple anchors the same way. Do not force everything into one anchor just because
it's simpler - identify concepts that genuinely need 2+ anchors and mark them that way.

Your task:
- Extract EVERY distinct business concept you can identify from this schema - do not limit
  yourself to a fixed count. Be exhaustive: cover sales, purchasing, inventory, production,
  HR, and customer-facing concepts wherever the schema supports them.
- Skip purely technical/administrative columns that aren't business concepts on their own
  (e.g. rowguid, ModifiedDate, foreign key ID columns used only for joins).
- For each concept, list one or more anchors. Each anchor must be an exact schema/table/column
  taken from the provided catalog only - never invent a schema, table, or column that isn't there.
  Follow the worked example above: identify which concepts genuinely need multiple anchors
  (margins, net amounts, ratios, anything computed by combining two different figures) versus
  which ones are simple single-column concepts.
- For each concept, list related_concepts: other concept names from your own proposed list that
  are closely related in business meaning. Use an empty list if there are none.
- Return ONLY a JSON array, no markdown code fences, no explanation, with these exact lowercase keys:
  [{"concept": "Revenue", "anchors": [{"schema": "Sales", "table": "SalesOrderDetail", "column": "LineTotal"}], "related_concepts": ["Order Total", "Profit"]}]
"""


def BuildRelationshipGraph() -> nx.MultiGraph:
    Conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    FkDf = pd.read_sql(
        """
        SELECT
            tc.table_schema   AS source_schema,
            tc.table_name     AS source_table,
            kcu.column_name   AS source_column,
            ccu.table_schema  AS target_schema,
            ccu.table_name    AS target_table,
            ccu.column_name   AS target_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
            AND tc.table_schema = rc.constraint_schema
        JOIN information_schema.key_column_usage ccu
            ON rc.unique_constraint_name = ccu.constraint_name
            AND rc.unique_constraint_schema = ccu.table_schema
            AND kcu.position_in_unique_constraint = ccu.ordinal_position
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema NOT IN ('information_schema', 'pg_catalog', 'public')
            AND tc.table_schema NOT LIKE 'pg_toast%'
        ORDER BY source_schema, source_table;
        """,
        Conn,
    )
    Conn.close()

    Graph = nx.MultiGraph()
    for _, Row in FkDf.iterrows():
        SourceNode = f'{Row["source_schema"]}.{Row["source_table"]}'
        TargetNode = f'{Row["target_schema"]}.{Row["target_table"]}'

        Graph.add_node(SourceNode, schema=Row["source_schema"], table=Row["source_table"])
        Graph.add_node(TargetNode, schema=Row["target_schema"], table=Row["target_table"])

        Graph.add_edge(
            SourceNode, TargetNode,
            source_column=Row["source_column"],
            target_column=Row["target_column"],
        )
    return Graph


def LoadSchemaCatalog(CatalogPath: str = "data/schema_catalog.json") -> list[dict]:
    with open(CatalogPath, "r") as F:
        return json.load(F)


def BuildSchemaSummary(Catalog: list[dict]) -> str:
    Lines = []
    for Entry in Catalog:
        Columns = ", ".join(Col["name"] for Col in Entry["columns"])
        Lines.append(f'{Entry["schema"]}.{Entry["table"]}: {Columns}')
    return "\n".join(Lines)


def StripCodeFences(Text: str) -> str:
    Text = Text.strip()
    Text = re.sub(r"^```(?:json)?\s*", "", Text)
    Text = re.sub(r"\s*```$", "", Text)
    return Text.strip()


def IsAnchorValid(Anchor: dict, ValidColumns: set[tuple[str, str, str]]) -> bool:
    return (Anchor.get("schema"), Anchor.get("table"), Anchor.get("column")) in ValidColumns


def AddConceptsToGraph(Graph: nx.MultiGraph) -> nx.MultiGraph:
    Catalog = LoadSchemaCatalog()
    SchemaSummary = BuildSchemaSummary(Catalog)
    ValidColumns = {
        (Entry["schema"], Entry["table"], Col["name"])
        for Entry in Catalog
        for Col in Entry["columns"]
    }

    Client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    UserPrompt = f"Schema catalog:\n{SchemaSummary}\n\nPropose the business concepts now."
    print("Calling Gemini for concept extraction (exhaustive mode - this can take a minute or two)...")
    Response = Client.models.generate_content(
        model=Model,
        contents=UserPrompt,
        config=types.GenerateContentConfig(
            system_instruction=SystemPrompt,
            http_options=types.HttpOptions(timeout=180000),
        ),
    )
    print("Gemini responded, parsing concepts...")
    Concepts = json.loads(StripCodeFences(Response.text))

    RejectedAnchorCount = 0
    SkippedConceptCount = 0
    AcceptedConcepts = []
    for Entry in Concepts:
        ValidAnchors = [A for A in Entry["anchors"] if IsAnchorValid(A, ValidColumns)]
        RejectedAnchorCount += len(Entry["anchors"]) - len(ValidAnchors)
        if not ValidAnchors:
            SkippedConceptCount += 1
            print(f'  Skipping concept "{Entry["concept"]}" - no valid anchors (all hallucinated)')
            continue
        Entry["anchors"] = ValidAnchors
        AcceptedConcepts.append(Entry)

    if RejectedAnchorCount:
        print(f"Rejected {RejectedAnchorCount} hallucinated anchor(s) across {len(Concepts)} proposed concepts "
              f"({SkippedConceptCount} concept(s) dropped entirely)")

    for Entry in AcceptedConcepts:
        ConceptNode = f'concept:{Entry["concept"]}'
        Graph.add_node(ConceptNode, type="concept", name=Entry["concept"])

        for Anchor in Entry["anchors"]:
            TableNode = f'{Anchor["schema"]}.{Anchor["table"]}'
            Graph.add_edge(ConceptNode, TableNode, relation="represented_by", column=Anchor["column"])

    for Entry in AcceptedConcepts:
        ConceptNode = f'concept:{Entry["concept"]}'
        for RelatedName in Entry["related_concepts"]:
            RelatedNode = f"concept:{RelatedName}"
            if RelatedNode in Graph.nodes:
                Graph.add_edge(ConceptNode, RelatedNode, relation="related_to")

    return Graph


def BuildAndSaveGraph(OutputPath: str = "data/knowledge_graph.gpickle") -> nx.MultiGraph:
    Graph = BuildRelationshipGraph()
    Graph = AddConceptsToGraph(Graph)

    os.makedirs(os.path.dirname(OutputPath), exist_ok=True)
    if hasattr(nx, "write_gpickle"):
        nx.write_gpickle(Graph, OutputPath)
    else:
        with open(OutputPath, "wb") as F:
            pickle.dump(Graph, F)

    TableNodeCount = sum(1 for _, D in Graph.nodes(data=True) if D.get("type") != "concept")
    ConceptNodeCount = sum(1 for _, D in Graph.nodes(data=True) if D.get("type") == "concept")

    FkEdgeCount = 0
    RepresentedByEdgeCount = 0
    RelatedToEdgeCount = 0
    for _, _, D in Graph.edges(data=True):
        Relation = D.get("relation")
        if Relation == "represented_by":
            RepresentedByEdgeCount += 1
        elif Relation == "related_to":
            RelatedToEdgeCount += 1
        else:
            FkEdgeCount += 1

    print(f"\nGraph saved to {OutputPath}")
    print(f"Total nodes: {Graph.number_of_nodes()}  (tables: {TableNodeCount}, concepts: {ConceptNodeCount})")
    print(f"Total edges: {Graph.number_of_edges()}  "
          f"(FK: {FkEdgeCount}, represented_by: {RepresentedByEdgeCount}, related_to: {RelatedToEdgeCount})")

    return Graph


if __name__ == "__main__":
    BuildAndSaveGraph()
