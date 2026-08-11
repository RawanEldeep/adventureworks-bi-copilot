import json
from rank_bm25 import BM25Okapi
from retrieval.preprocessing import TextProcessing


def build_document(entry: dict) -> str:
    """Flatten one schema catalog entry (schema, table, columns) into a
    single text string - the "document" BM25 will index for that table."""
    return " ".join([entry["schema"], entry["table"]] + entry["columns"])


class KeywordRetriever:
    def __init__(self, catalog_path: str = "data/schema_catalog.json"):
        with open(catalog_path, "r") as f:
            catalog = json.load(f)

        self.entries = catalog
        self.corpus = [TextProcessing(build_document(entry)) for entry in catalog]
        self.bm25 = BM25Okapi(self.corpus)

    def retrieve(self, question: str, top_k: int = 5) -> list[dict]: 
        query_tokens = TextProcessing(question)
        if not query_tokens: 
            return []

        scores = self.bm25.get_scores(query_tokens)
        scored_entries = list(zip(scores, self.entries))
        scored_entries.sort(key=lambda pair: pair[0], reverse=True)

        results = []
        for score, entry in scored_entries[:top_k]: 
            result = dict(entry)
            result["_score"] = round(float(score), 2)
            results.append(result)

        return results 