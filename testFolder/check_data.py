import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=5432, dbname='poseidon', user='poseidon',
    password=os.environ["DB_PASSWORD"], sslmode='require', connect_timeout=10,
)
cur = conn.cursor()

def show(title, sql):
    print(f"\n== {title}")
    cur.execute(sql)
    for row in cur.fetchall():
        print("  ", row)

show("1. total rows in award_history", "SELECT COUNT(*) FROM award_history")

show("2. loader status (done / failed counts)",
     "SELECT status, COUNT(*), MAX(rows_loaded) FROM load_progress GROUP BY status")

show("3. failed slices, if any",
     "SELECT fy, naics, agency, LEFT(error, 80) FROM load_progress WHERE status <> 'done' LIMIT 10")

show("4. rows per start year",
     "SELECT EXTRACT(YEAR FROM start_date)::int AS yr, COUNT(*) FROM award_history GROUP BY 1 ORDER BY 1")

show("5. missing values (rows with null)",
     """SELECT COUNT(*) FILTER (WHERE vendor_uei IS NULL) AS no_uei,
               COUNT(*) FILTER (WHERE end_date IS NULL)   AS no_end,
               COUNT(*) FILTER (WHERE psc_code IS NULL)   AS no_psc,
               COUNT(*) FILTER (WHERE description IS NULL OR description = '') AS no_desc
        FROM award_history""")

show("6. standalone contracts (what the matcher uses)",
     "SELECT COUNT(*) FROM award_history WHERE award_id LIKE '%-NONE-%-NONE-'")

show("7. labeled pairs in recompete_training (total, kept)",
     "SELECT COUNT(*), SUM(retained::int) FROM recompete_training")

conn.close()