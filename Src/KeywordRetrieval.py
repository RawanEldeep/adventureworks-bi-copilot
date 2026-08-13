import json
from rank_bm25 import BM25Okapi
from Preprocessing import TextProcessing


def BuildDocument(Entry: dict) -> str:
    """Flatten one schema catalog entry (schema, table, columns) into a
    single text string - the "document" BM25 will index for that table."""
    ColumnNames = [Col["name"] for Col in Entry["columns"]]
    return " ".join([Entry["schema"], Entry["table"]] + ColumnNames)


class KeywordRetriever:
    def __init__(self, CatalogPath: str = "data/schema_catalog.json"):
        with open(CatalogPath, "r") as F:
            Catalog = json.load(F)

        self.Entries = Catalog
        self.Corpus = [TextProcessing(BuildDocument(Entry)) for Entry in Catalog]
        self.Bm25 = BM25Okapi(self.Corpus)

    def Retrieve(self, Question: str, TopK: int = 5) -> list[dict]:
        QueryTokens = TextProcessing(Question)
        if not QueryTokens:
            return []

        Scores = self.Bm25.get_scores(QueryTokens)
        ScoredEntries = list(zip(Scores, self.Entries))
        ScoredEntries.sort(key=lambda Pair: Pair[0], reverse=True)

        Results = []
        for Score, Entry in ScoredEntries[:TopK]:
            Result = dict(Entry)
            Result["_score"] = round(float(Score), 2)
            Results.append(Result)

        return Results