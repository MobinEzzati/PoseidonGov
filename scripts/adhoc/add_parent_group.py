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

cur.execute("ALTER TABLE entity ADD COLUMN IF NOT EXISTS parent_group text")

cur.execute("""
    UPDATE entity SET parent_group = CASE
        WHEN vendor_group LIKE 'NORTHROP GRUMMAN%' THEN 'NORTHROP GRUMMAN'
        WHEN vendor_group LIKE 'L3HARRIS%' OR vendor_group LIKE 'L3 %' THEN 'L3HARRIS'
        WHEN vendor_group LIKE 'RAYTHEON%' OR vendor_group LIKE 'RTX%' THEN 'RTX'
        WHEN vendor_group LIKE 'BAE SYSTEMS%' THEN 'BAE SYSTEMS'
        WHEN vendor_group LIKE 'GENERAL ELECTRIC%' OR vendor_group LIKE 'GE %' THEN 'GENERAL ELECTRIC'
        WHEN vendor_group LIKE 'LOCKHEED MARTIN%' THEN 'LOCKHEED MARTIN'
        WHEN vendor_group LIKE 'BOEING%' THEN 'BOEING'
        WHEN vendor_group LIKE 'HONEYWELL%' THEN 'HONEYWELL'
        WHEN vendor_group LIKE 'GENERAL DYNAMICS%' THEN 'GENERAL DYNAMICS'
        ELSE vendor_group
    END
""")
conn.commit()

cur.execute("""
    SELECT e.parent_group,
           COUNT(DISTINCT e.uei) AS n_ueis,
           COUNT(*) AS n_contracts,
           ROUND(SUM(h.total_value) / 1e9, 2) AS total_billions
    FROM entity e
    JOIN award_history h ON h.vendor_uei = e.uei
    GROUP BY e.parent_group
    ORDER BY SUM(h.total_value) DESC
    LIMIT 15
""")
print(f"{'parent group':32s} {'UEIs':>5s} {'contracts':>10s} {'$B':>8s}")
for g, n, c, b in cur.fetchall():
    print(f"{g[:32]:32s} {n:5d} {c:10d} {b:8}")

cur.close()
conn.close()