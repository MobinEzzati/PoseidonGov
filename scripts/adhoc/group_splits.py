import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=5432, dbname="poseidon", user="poseidon",
    password=os.environ["DB_PASSWORD"], sslmode="require", connect_timeout=10,
)
cur = conn.cursor()

prefixes = ["NORTHROP", "L3", "RAYTHEON", "RTX", "BAE", "GENERAL ELECTRIC",
            "GE ", "LOCKHEED", "BOEING", "HONEYWELL", "GENERAL DYNAMICS"]

for p in prefixes:
    cur.execute("""
        SELECT vendor_group, COUNT(*) AS n_ueis
        FROM entity
        WHERE vendor_group LIKE %s
        GROUP BY vendor_group
        ORDER BY n_ueis DESC
    """, (p + "%",))
    rows = cur.fetchall()
    print(f"\n{p}")
    for group, n in rows:
        print(f"  {n:3d}  {group}")

cur.close()
conn.close()