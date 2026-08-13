import os
from google import genai
from google.genai import types

Model = "gemini-3.6-flash"

def _FormatSchemaContext(Retrieved: list[dict]) -> str:
    Lines = []
    for Entry in Retrieved:
        Cols = ", ".join(Col["name"] for Col in Entry["columns"])
        Lines.append(f'-"{Entry["schema"]}"."{Entry["table"]}"(columns:{Cols})')
    return "\n".join(Lines)
SystemPrompt = """You are an SQL generation engine for the Adventureworks Postgres database.

Rules:
- Use ONLY the tables and columns provided in the schema context below. Do not invent tables or columns.
- All schema and table names are case-sensitive in Postgres and MUST be doubled-quoted, e.g "Sales"."SalesOrderHeader".
- If the provided schema context is insufficient to answer the question, say so explicitly instead of guessing at table/column names.
- Return ONLY the SQL query, no explanation, no markdown code fences.
"""
class SQLGenerator:
    def __init__(self, ApiKey: str | None = None):
        self.Client = genai.Client(api_key=ApiKey or os.environ.get("GEMINI_API_KEY"))

    def Generate(self, Question : str, RetrievedSchema: list[dict]) -> str:
        if not RetrievedSchema:
            return "-- No relevant tables found for this question. Try rephrasing."
        SchemaContext = _FormatSchemaContext(RetrievedSchema)
        UserPrompt = (
            f"Schema context (retrieved as relevant to the question): \n {SchemaContext}\n\n"
            f"Question:{Question}\n\n"
            f"Generated the SQL query."
        )
        Response = self.Client.models.generate_content(
            model=Model,
            contents=UserPrompt,
            config=types.GenerateContentConfig(system_instruction=SystemPrompt,), )
        return Response.text.strip()