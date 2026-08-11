import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd
load_dotenv()
print(repr(os.getenv("DB_PASSWORD")))

# ─────────────────────────────────────────────
# Database connection
# ─────────────────────────────────────────────

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

tables = pd.read_sql(
    """
    SELECT
        table_schema,
        table_name
    FROM information_schema.tables
    WHERE table_schema IN (
        'Sales',
        'Person',
        'Production'
    )
    ORDER BY
        table_schema,
        table_name;
    """,
    conn
)

print(tables)

# ─────────────────────────────────────────────
# Inspect each table
# ─────────────────────────────────────────────

for _, row in tables.iterrows():

    schema = row["table_schema"]
    table = row["table_name"]

    print("=" * 100)
    print(f"{schema}.{table}")

    total = pd.read_sql(
        f"""
        SELECT COUNT(*) AS total
        FROM "{schema}"."{table}";
        """,
        conn
    ).iloc[0]["total"]

    print("Total Count of Rows:", total)

    df = pd.read_sql(
        f"""
        SELECT *
        FROM "{schema}"."{table}"
        LIMIT 3;
        """,
        conn
    )

    print(df)

# ─────────────────────────────────────────────
# Close connection
# ─────────────────────────────────────────────

conn.close()