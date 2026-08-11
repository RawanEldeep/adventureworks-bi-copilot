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

from retrieval.keyword_retrieval import KeywordRetriever
from llm.sql_generator import SQLGenerator

load_dotenv()

def main():
    retriever = KeywordRetriever()
    generator = SQLGenerator()

    question = input("Ask a buisness question: ")
    print(f"You asked: {question}")

    results = retriever.retrieve(question, top_k=5)
    print("\nTop matching tables:")
    if not results: 
        print("No matches found")
    for entry in results:
        print(f"  {entry['schema']}.{entry['table']}  (score: {entry['_score']})")
    sql = generator.generate(question, results)
    print("\nGenerated SQL:")
    print(sql)
    
if __name__ == "__main__":
    main()

