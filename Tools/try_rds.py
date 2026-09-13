import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

# conn = psycopg2.connect(
#     host=os.environ.get("DB_HOST"),
#     port=5432,
#     dbname="poseidon",
#     user=os.environ.get("DB_USER"),
#     password=os.environ.get("DB_PASSWORD"),
#     sslmode="require"
# )

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="poseidon",
    user="poseidon",
    password="localdev",
)


cur = conn.cursor()

cur.execute("SELECT count(*) FROM award")
print("Awards:", cur.fetchone()[0])

cur.execute("SELECT count(*) FROM risk_score")
print("Risk scores:", cur.fetchone()[0])


cur.execute("SELECT recipient_name, amount FROM award ORDER BY amount DESC LIMIT 5")
for r in cur.fetchall():
    print(f"{r[0][:40]:40} ${r[1]:>15,.2f}")


cur.execute("SELECT count(*) FROM aircraft")
print("Aircraft:", cur.fetchone()[0])
cur.close()
conn.close()