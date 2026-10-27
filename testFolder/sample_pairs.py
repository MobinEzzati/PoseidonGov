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

cur.execute("SELECT COUNT(*), SUM(retained::int) FROM recompete_training")
total, kept = cur.fetchone()
print(f"{total} pairs in table, {kept} kept ({kept / total:.0%})\n")

cur.execute("""
    SELECT t.retained, round(t.match_confidence::numeric, 2),
           o.vendor_name, o.end_date, o.description,
           n.vendor_name, n.start_date, n.description
    FROM recompete_training t
    JOIN award_history o ON o.award_id = t.old_award_id
    JOIN award_history n ON n.award_id = t.next_award_id
    ORDER BY random() LIMIT 20
""")
for kept_flag, sim, ov, oe, od, nv, ns, nd in cur.fetchall():
    print(f"[{'KEPT' if kept_flag else 'LOST'}]  similarity {sim}")
    print(f"  OLD: {ov}  (ended {oe})\n       {(od or '')[:90]}")
    print(f"  NEW: {nv}  (started {ns})\n       {(nd or '')[:90]}\n")
conn.close()