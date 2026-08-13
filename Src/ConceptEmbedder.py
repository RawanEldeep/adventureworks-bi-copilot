import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from GraphLoader import LoadGraph


def GetConceptDisplayName(Graph, Node: str) -> str:
    return Graph.nodes[Node].get("name", Node)


def ExtractConceptInfo(Graph, ConceptNode: str) -> tuple[list[str], list[str]]:
    # The graph can contain duplicate parallel `related_to` edges for the same pair of
    # concepts (added once from each side's related_concepts list) - dedupe defensively
    # here rather than in GraphBuilder.py, since that graph-construction logic is off-limits.
    Anchors = []
    RelatedNames = []
    SeenAnchors = set()
    SeenRelated = set()
    for U, V, D in Graph.edges(ConceptNode, data=True):
        Other = V if U == ConceptNode else U
        Relation = D.get("relation")
        if Relation == "represented_by":
            Anchor = f'{Other}.{D["column"]}'
            if Anchor not in SeenAnchors:
                SeenAnchors.add(Anchor)
                Anchors.append(Anchor)
        elif Relation == "related_to":
            RelatedName = GetConceptDisplayName(Graph, Other)
            if RelatedName not in SeenRelated:
                SeenRelated.add(RelatedName)
                RelatedNames.append(RelatedName)
    return Anchors, RelatedNames


def BuildConceptDocument(Name: str, Anchors: list[str], RelatedNames: list[str]) -> str:
    Text = Name
    if Anchors:
        Text += ". Anchors: " + ", ".join(Anchors)
    if RelatedNames:
        Text += ". Related: " + ", ".join(RelatedNames)
    return Text


def BuildCollection(Path: str = "data/chroma_db"):
    Client = chromadb.PersistentClient(path=Path)
    EmbeddingFn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return Client.get_or_create_collection(
        name="business_concepts",
        embedding_function=EmbeddingFn,
    )


def EmbedConcepts() -> dict:
    Graph = LoadGraph()
    Collection = BuildCollection()

    Ids = []
    Documents = []
    Metadatas = []
    ZeroAnchorCount = 0

    for Node, Data in Graph.nodes(data=True):
        if Data.get("type") != "concept":
            continue

        Name = Data.get("name", Node)
        Anchors, RelatedNames = ExtractConceptInfo(Graph, Node)
        if not Anchors:
            ZeroAnchorCount += 1
            print(f'  WARNING: concept "{Name}" has zero anchors')

        Document = BuildConceptDocument(Name, Anchors, RelatedNames)

        Ids.append(Name)
        Documents.append(Document)
        Metadatas.append({
            "anchors": ", ".join(Anchors),
            "related_concepts": ", ".join(RelatedNames),
        })

    Collection.upsert(ids=Ids, documents=Documents, metadatas=Metadatas)

    return {
        "Collection": Collection,
        "Ids": Ids,
        "Documents": Documents,
        "ZeroAnchorCount": ZeroAnchorCount,
    }


if __name__ == "__main__":
    Result = EmbedConcepts()
    Collection = Result["Collection"]

    print(f"\nConcepts upserted: {len(Result['Ids'])}")
    if Result["Documents"]:
        print(f"First concept document: {Result['Documents'][0]!r}")
    print(f"Concepts with zero anchors: {Result['ZeroAnchorCount']}")
    print(f"Collection count: {Collection.count()}")

    QueryText = "how much revenue did we make"
    QueryResult = Collection.query(query_texts=[QueryText], n_results=3)
    print(f"\nTest query: {QueryText!r}")
    for Name, Distance in zip(QueryResult["ids"][0], QueryResult["distances"][0]):
        print(f"  {Name}  (distance: {Distance:.4f})")
