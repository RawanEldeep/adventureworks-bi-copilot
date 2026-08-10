# Buisness Intelligence Copilot 



A natural-language business intelligence agent that answers questions over a relational database using Large Language Models (LLMs) and Knowledge Graphs (KGs). The retrieved context is passed to the LLM to generate accurate SQL queries answering the user's question.



## Database



This project uses the AdventureWorks database, Microsoft's official sample enterprise database, served via Docker using the `chriseaton/adventureworks:postgres` image.



## Setup



1\. `copy .env.example .env` and fill in real values

2\. `docker compose up -d`

3\. `pip install -r requirements.txt`

4\. `python src\\main.py`

