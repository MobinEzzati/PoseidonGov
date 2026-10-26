import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host="poseidongov-db.cf6s0y8eqhz4.us-east-1.rds.amazonaws.com",
    port=5432, dbname="poseidon", user="poseidon",
    password=os.environ["DB_PASSWORD"], sslmode="require", connect_timeout=10,
)
cur = conn.cursor()

cur.execute("""
    INSERT INTO entity (uei, name, naics_primary, first_seen, last_seen)
    SELECT vendor_uei,
           (array_agg(vendor_name ORDER BY start_date DESC NULLS LAST))[1],
           mode() WITHIN GROUP (ORDER BY naics_code),
           MIN(start_date),
           MAX(start_date)
    FROM award_history
    WHERE vendor_uei IS NOT NULL
    GROUP BY vendor_uei
    ON CONFLICT (uei) DO UPDATE
      SET name = EXCLUDED.name,
          naics_primary = EXCLUDED.naics_primary,
          first_seen = EXCLUDED.first_seen,
          last_seen = EXCLUDED.last_seen
""")
conn.commit()

cur.execute("SELECT COUNT(*) FROM entity")
print("entity rows:", cur.fetchone()[0])
cur.close()
conn.close()