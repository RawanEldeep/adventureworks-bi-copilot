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
def main():
    question = input("Ask a buisness question: ")
    print(f"You asked: {question}")


if __name__ == "__main__":
    main()

