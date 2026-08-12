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
    conn
)

Fk_df = pd.read_sql(
    """
    SELECT 
        tc.table_schema AS source_schema, 
        tc.table_name AS source_table, 
        kcu.column_name AS source_column, 
        ccu.table_schema AS target_schema, 
        ccu.table_name AS target_table, 
        ccu.column_name AS target_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name 
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
        AND  tc.table_schema = ccu.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema NOT IN ('information_schema', 'pg_catalog', 'public') AND tc.table_schema NOT LIKE 'pg_toast%'
    ORDER BY 
        source_schema, 
        source_table; 
    """, conn
    )


print(f"\n Column Dataframe:{columns_df}")
print(f"\n FK Dataframe:{Fk_df}")
conn.close()

SCHEMA_CATALOG = [
        {
        "schema" : schema, 
        "table" : table, 
        "columns" :[
            {"name" : name, "type": dtype}
            for name, dtype in zip(group["column_name"], group["data_type"])
        ], 

     } 
    for (schema, table), group in columns_df.groupby(["table_schema", "table_name"])
]

FOREIGN_KEYS = Fk_df.to_dict(orient="records")
conn.close()
os.makedirs("data", exist_ok=True)
with open("data/schema_catalog.json", "w") as f:
    json.dump(SCHEMA_CATALOG, f, indent=2)

with open("data/foreign_keys.json", "w") as f: 
    json.dump(FOREIGN_KEYS, f, indent=2)