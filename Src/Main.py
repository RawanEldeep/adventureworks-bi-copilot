
"""
Buisness Intelligence Copilot

Pipeline:
Natural Language Question
-> KnowledgeGraph traversal & Keyword Search
-> Relevant Concepts and tables
-> LLM
-> Generated SQL
-> Answer

"""
from Retriever import HybridRetriever
from SQLGenerator import SQLGenerator

QuitCommands = {"quit", "exit"}


def PrintRetrieved(Retrieved: dict) -> None:
    print(f"Tables: {Retrieved['tables']}")
    print(f"Joins: {Retrieved['joins']}")
    print(f"Matched concepts: {Retrieved['matched_concepts']}")


def Main():
    print("Loading retriever and SQL generator (this can take a moment)...")
    Retriever = HybridRetriever()
    Generator = SQLGenerator()
    print("Ready. Ask a business question, or type 'quit'/'exit' to stop.\n")

    while True:
        Question = input("Ask a business question: ").strip()
        if not Question or Question.lower() in QuitCommands:
            print("Goodbye.")
            break

        print(f"\n{'=' * 70}")
        print(f"Question: {Question}")
        print("=" * 70)

        try:
            Retrieved = Retriever.Retrieve(Question)
        except Exception as E:
            print(f"[ERROR] Retrieval failed: {E}")
            print("Try again with a different question.\n")
            continue

        PrintRetrieved(Retrieved)

        try:
            Sql = Generator.Generate(Question, Retrieved)
            print("\nGenerated SQL:")
            print(Sql)
        except Exception as E:
            print(f"\n[ERROR] SQL generation failed: {E}")
            print("(Retrieval above succeeded - only SQL generation failed.)")

        print()


if __name__ == "__main__":
    Main()
