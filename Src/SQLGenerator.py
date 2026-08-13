import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from ConceptEmbedder import ExtractConceptInfo
from GraphLoader import LoadGraph

load_dotenv()

Model = "gemini-3.6-flash"

SystemPrompt = """You are an SQL generation engine for the Adventureworks Postgres database.

Rules:
- Use ONLY the tables and columns provided in the schema context below. Do not invent tables or columns.
- All schema and table names are case-sensitive in Postgres and MUST be doubled-quoted, e.g "Sales"."SalesOrderHeader".
- If join paths are provided below, use them directly to connect tables - they are pre-verified,
  correct foreign-key relationships. Do not infer or guess your own join logic when a join path
  covering the tables you need is already given.
- If related business concepts are provided below, use their anchor columns as guidance when the
  question uses business language (e.g. "profit", "churn") that doesn't literally match a column name -
  the anchors tell you which column(s) actually represent that concept.
- If the provided schema context is insufficient to answer the question, say so explicitly instead of guessing at table/column names.
- Return ONLY the SQL query, no explanation, no markdown code fences.
"""


def GetColumnsForTables(Tables: list[str], CatalogPath: str = "data/schema_catalog.json") -> list[dict]:
    with open(CatalogPath, "r") as F:
        Catalog = json.load(F)

    TableSet = set(Tables)
    return [
        Entry for Entry in Catalog
        if f'{Entry["schema"]}.{Entry["table"]}' in TableSet
    ]


def GetConceptAnchors(Graph, ConceptName: str) -> list[str]:
    ConceptNode = f"concept:{ConceptName}"
    if ConceptNode not in Graph.nodes:
        return []
    Anchors, _ = ExtractConceptInfo(Graph, ConceptNode)
    return Anchors


def _FormatSchemaContext(Columns: list[dict]) -> str:
    Lines = []
    for Entry in Columns:
        Cols = ", ".join(Col["name"] for Col in Entry["columns"])
        Lines.append(f'-"{Entry["schema"]}"."{Entry["table"]}"(columns:{Cols})')
    return "\n".join(Lines) if Lines else "(none)"


def _FormatJoinContext(Joins: list[str]) -> str:
    if not Joins:
        return "(no pre-verified join paths available - infer joins carefully from the schema above if needed)"
    return "\n".join(f"- {Join}" for Join in Joins)


def _FormatConceptContext(MatchedConcepts: list[dict], Graph) -> str:
    if not MatchedConcepts:
        return "(none)"
    Lines = []
    for Match in MatchedConcepts:
        ConceptName = Match["concept_name"]
        Anchors = GetConceptAnchors(Graph, ConceptName)
        if Anchors:
            Lines.append(f'{ConceptName} -> {", ".join(Anchors)}')
    return "\n".join(Lines) if Lines else "(none)"


class SQLGenerator:
    def __init__(self, ApiKey: str | None = None):
        self.Client = genai.Client(api_key=ApiKey or os.environ.get("GEMINI_API_KEY"))
        self.Graph = LoadGraph()

    def Generate(self, Question: str, Retrieved: dict) -> str:
        if not Retrieved["tables"]:
            return "-- No relevant tables found for this question. Try rephrasing."

        Columns = GetColumnsForTables(Retrieved["tables"])
        SchemaContext = _FormatSchemaContext(Columns)
        JoinContext = _FormatJoinContext(Retrieved["joins"])
        ConceptContext = _FormatConceptContext(Retrieved["matched_concepts"], self.Graph)

        UserPrompt = (
            f"Schema context (retrieved as relevant to the question):\n{SchemaContext}\n\n"
            f"Join paths (pre-verified, use these directly):\n{JoinContext}\n\n"
            f"Related business concepts (business-language hints, may or may not apply):\n{ConceptContext}\n\n"
            f"Question: {Question}\n\n"
            f"Generate the SQL query."
        )
        Response = self.Client.models.generate_content(
            model=Model,
            contents=UserPrompt,
            config=types.GenerateContentConfig(system_instruction=SystemPrompt,), )
        return Response.text.strip()


if __name__ == "__main__":
    from Retriever import HybridRetriever

    Question = "What's our profit margin?"
    Retrieved = HybridRetriever().Retrieve(Question)

    Columns = GetColumnsForTables(Retrieved["tables"])
    Graph = LoadGraph()
    print("=== SCHEMA CONTEXT ===")
    print(_FormatSchemaContext(Columns))
    print("\n=== JOIN CONTEXT ===")
    print(_FormatJoinContext(Retrieved["joins"]))
    print("\n=== CONCEPT CONTEXT ===")
    print(_FormatConceptContext(Retrieved["matched_concepts"], Graph))

    Sql = SQLGenerator().Generate(Question, Retrieved)
    print("\n=== GENERATED SQL ===")
    print(Sql)
