import os
import json
from dotenv import load_dotenv
import psycopg2
import pandas as pd

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

# ─────────────────────────────────────────────
# Get tables
# ─────────────────────────────────────────────

columns_df = pd.read_sql(
    """
    SELECT
        table_schema,
        table_name, 
        column_name
    FROM information_schema.columns
    WHERE table_schema NOT IN (
        'information_schema', 'pg_catalog', 'public') AND table_schema NOT LIKE 'pg_toast%'

    ORDER BY
        table_schema,
        table_name,
        ordinal_position;
    """,
    conn
)

conn.close()
print(columns_df)

SCHEMA_CATALOG = [
    {"schema" : schema, "table" : table, "columns" : group["column_name"].tolist()}
    for (schema, table), group in columns_df.groupby(["table_schema", "table_name"])
    ]

os.makedirs("data", exist_ok=True)
with open("data/schema_catalog.json", "w") as f:
    json.dump(SCHEMA_CATALOG, f, indent=2)