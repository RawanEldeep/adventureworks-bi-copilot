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
from dotenv import load_dotenv

from KeywordRetrieval import KeywordRetriever
from SQLGenerator import SQLGenerator

load_dotenv()

def Main():
    Retriever = KeywordRetriever()
    Generator = SQLGenerator()

    Question = input("Ask a buisness question: ")
    print(f"You asked: {Question}")

    Results = Retriever.Retrieve(Question, TopK=5)
    print("\nTop matching tables:")
    if not Results:
        print("No matches found")
    for Entry in Results:
        print(f"  {Entry['schema']}.{Entry['table']}  (score: {Entry['_score']})")
    Sql = Generator.Generate(Question, Results)
    print("\nGenerated SQL:")
    print(Sql)

if __name__ == "__main__":
    Main()

