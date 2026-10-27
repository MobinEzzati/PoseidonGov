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

cur.execute("""
    SELECT r.recipient_name, COUNT(DISTINCT h.vendor_uei) AS n_ueis
    FROM (SELECT DISTINCT recipient_name FROM risk_score) r
    LEFT JOIN award_history h
           ON UPPER(TRIM(h.vendor_name)) = UPPER(TRIM(r.recipient_name))
    GROUP BY r.recipient_name
""")
rows = cur.fetchall()

print("10 names with NO match")
for name, n in [x for x in rows if x[1] == 0][:10]:
    print(f"  {name}")

print("\n5 names with the MOST UEIs")
for name, n in sorted(rows, key=lambda x: -x[1])[:5]:
    print(f"  {n:3d}  {name}")

print("\nNAICS in the old award table")
cur.execute("SELECT naics_code, COUNT(*) FROM award GROUP BY naics_code ORDER BY 2 DESC")
for naics, n in cur.fetchall():
    print(f"  {naics}: {n}")

cur.close()
conn.close()