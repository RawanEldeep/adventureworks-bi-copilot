import os
from google import genai
from google.genai import types 

MODEL = "gemini-3.6-flash"

def _format_schema_context(retrieved: list[dict]) -> str: 
    lines = []
    for entry in retrieved: 
        cols = ", ".join(col["name"] for col in entry["columns"])
        lines.append(f'-"{entry["schema"]}"."{entry["table"]}"(columns:{cols})')
    return "\n".join(lines)
SYSTEM_PROMPT = """You are an SQL generation engine for the Adventureworks Postgres database.

Rules: 
- Use ONLY the tables and columns provided in the schema context below. Do not invent tables or columns.
- All schema and table names are case-sensitive in Postgres and MUST be doubled-quoted, e.g "Sales"."SalesOrderHeader".
- If the provided schema context is insufficient to answer the question, say so explicitly instead of guessing at table/column names. 
- Return ONLY the SQL query, no explanation, no markdown code fences.
"""
class SQLGenerator: 
    def __init__(self, api_key: str | None = None): 
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    def generate(self, question : str, retrieved_schema: list[dict]) -> str: 
        if not retrieved_schema: 
            return "-- No relevant tables found for this question. Try rephrasing."
        schema_context = _format_schema_context(retrieved_schema)
        user_prompt = (
            f"Schema context (retrieved as relevant to the question): \n {schema_context}\n\n"
            f"Question:{question}\n\n"
            f"Generated the SQL query."
        )
        response = self.client.models.generate_content(
            model=MODEL,
            contents=user_prompt, 
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,), )
        return response.text.strip()