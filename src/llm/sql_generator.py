import os
from google import genai
from google.genai import types 

MODEL = "gemini-2.5-flash"


class SQLGenerator: 
    def __init__(self, api_key: str | None = none): 
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    def generate(self, question : str, retrieved_schema: list[dict]) -> str: 
        