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

cur.execute("ALTER TABLE entity ADD COLUMN IF NOT EXISTS vendor_group text")

cur.execute(r"""
    UPDATE entity
    SET vendor_group = TRIM(regexp_replace(
        regexp_replace(
            regexp_replace(UPPER(name), '[^A-Z0-9 ]', '', 'g'),
            '\m(THE|INC|LLC|CORP|CORPORATION|COMPANY|CO|LTD|LP|LLP)\M', '', 'g'),
        '\s+', ' ', 'g'))
""")
conn.commit()

cur.execute("""
    SELECT vendor_group, COUNT(*) AS n_ueis
    FROM entity
    GROUP BY vendor_group
    ORDER BY n_ueis DESC
    LIMIT 15
""")
print("Groups with the most UEIs")
for group, n in cur.fetchall():
    print(f"  {n:3d}  {group}")

cur.close()
conn.close()