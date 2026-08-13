import networkx as nx

from ConceptEmbedder import BuildCollection, ExtractConceptInfo
from GraphLoader import LoadGraph
from KeywordRetrieval import KeywordRetriever

# ─────────────────────────────────────────────
# Semantic retrieval (Chroma)
# ─────────────────────────────────────────────

def RetrieveConcepts(Collection, Question: str, TopK: int = 5) -> list[dict]:
    QueryResult = Collection.query(query_texts=[Question], n_results=TopK)
    Matches = [
        {"concept_name": Name, "distance": Distance}
        for Name, Distance in zip(QueryResult["ids"][0], QueryResult["distances"][0])
    ]
    Matches.sort(key=lambda M: M["distance"])
    return Matches


# ─────────────────────────────────────────────
# Graph traversal
# ─────────────────────────────────────────────

def ExpandFromConcepts(Graph: nx.MultiGraph, ConceptNames: list[str]) -> set[str]:
    Tables = set()
    for Name in ConceptNames:
        ConceptNode = f"concept:{Name}"
        if ConceptNode not in Graph.nodes:
            continue
        Anchors, _ = ExtractConceptInfo(Graph, ConceptNode)
        for Anchor in Anchors:
            TableName = Anchor.rsplit(".", 1)[0]  # "Schema.Table.Column" -> "Schema.Table"
            Tables.add(TableName)
    return Tables


def BuildFkOnlySubgraph(Graph: nx.MultiGraph) -> nx.MultiGraph:
    """FK edges have no `relation` attribute (only `represented_by`/`related_to` edges do) -
    filter those out so join-path search doesn't route through concept nodes."""
    FkGraph = nx.MultiGraph()
    for U, V, K, D in Graph.edges(keys=True, data=True):
        if D.get("relation") is None:
            FkGraph.add_edge(U, V, key=K, **D)
    return FkGraph


def FindJoinPaths(Graph: nx.MultiGraph, TableList: list[str], MaxHops: int = 2) -> list[str]:
    FkGraph = BuildFkOnlySubgraph(Graph)
    UniqueTables = list(dict.fromkeys(TableList))
    SeenEdges = {}  # frozenset of the two endpoints -> formatted join string, dedupes regardless of traversal direction

    for I, Source in enumerate(UniqueTables):
        for Target in UniqueTables[I + 1:]:
            if Source not in FkGraph.nodes or Target not in FkGraph.nodes:
                continue
            try:
                Path = nx.shortest_path(FkGraph, Source, Target)
            except nx.NetworkXNoPath:
                continue

            # A path this long is almost certainly snaking through irrelevant bridge tables
            # rather than reflecting a real relationship between the two matched tables -
            # skip it rather than presenting a misleading join chain as authoritative.
            if len(Path) - 1 > MaxHops:
                continue

            for HopIndex in range(len(Path) - 1):
                A, B = Path[HopIndex], Path[HopIndex + 1]
                EdgeData = list(FkGraph[A][B].values())[0]
                SourceEndpoint = f'{A}.{EdgeData["source_column"]}'
                TargetEndpoint = f'{B}.{EdgeData["target_column"]}'
                EdgeKey = frozenset((SourceEndpoint, TargetEndpoint))
                if EdgeKey not in SeenEdges:
                    SeenEdges[EdgeKey] = f'{SourceEndpoint} = {TargetEndpoint}'

    return list(SeenEdges.values())


# ─────────────────────────────────────────────
# Hybrid merge
# ─────────────────────────────────────────────

class HybridRetriever:
    def __init__(self):
        self.Graph = LoadGraph()
        self.Keyword = KeywordRetriever()
        self.Collection = BuildCollection()

    def Retrieve(self, Question: str, TopK: int = 5) -> dict:
        KeywordResults = self.Keyword.Retrieve(Question, TopK=TopK)
        # A BM25 score of 0 means zero token overlap - not a weak match, no match at all -
        # so it's always safe to drop, unlike an arbitrary relative/absolute cutoff.
        RelevantKeywordResults = [Entry for Entry in KeywordResults if Entry["_score"] > 0]
        TableSetA = {f'{Entry["schema"]}.{Entry["table"]}' for Entry in RelevantKeywordResults}

        ConceptMatches = RetrieveConcepts(self.Collection, Question, TopK=TopK)
        ConceptNames = [M["concept_name"] for M in ConceptMatches]
        TableSetB = ExpandFromConcepts(self.Graph, ConceptNames)

        AllTables = TableSetA | TableSetB
        JoinPaths = FindJoinPaths(self.Graph, list(AllTables))

        return {
            "tables": sorted(AllTables),
            "joins": JoinPaths,
            "matched_concepts": ConceptMatches,
        }


if __name__ == "__main__":
    Retriever = HybridRetriever()

    TestQuestions = [
        "How many vacation hours does each employee have?",
        "What is the list price of each product sold in every sales order line?",
        "What's our profit margin?",
    ]

    for Question in TestQuestions:
        print(f"\n{'=' * 70}")
        print(f"Question: {Question}")
        print("=" * 70)
        Result = Retriever.Retrieve(Question)
        print(f"Tables: {Result['tables']}")
        print(f"Joins: {Result['joins']}")
        print(f"Matched concepts: {Result['matched_concepts']}")
