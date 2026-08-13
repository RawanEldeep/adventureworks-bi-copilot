import os
import json
from dotenv import load_dotenv
import psycopg2
import pandas as pd

load_dotenv()

Conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

# ─────────────────────────────────────────────
# Get tables
# ─────────────────────────────────────────────

ColumnsDf = pd.read_sql(
    """
    SELECT
        table_schema,
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema NOT IN (
        'information_schema', 'pg_catalog', 'public') AND table_schema NOT LIKE 'pg_toast%'

    ORDER BY
        table_schema,
        table_name,
        ordinal_position;
    """,
    Conn
)

print(f"\n Column Dataframe:{ColumnsDf}")
Conn.close()

SchemaCatalog = [
        {
        "schema" : Schema,
        "table" : Table,
        "columns" :[
            {"name" : Name, "type": Dtype}
            for Name, Dtype in zip(Group["column_name"], Group["data_type"])
        ],

     }
    for (Schema, Table), Group in ColumnsDf.groupby(["table_schema", "table_name"])
]

os.makedirs("data", exist_ok=True)
with open("data/schema_catalog.json", "w") as F:
    json.dump(SchemaCatalog, F, indent=2)