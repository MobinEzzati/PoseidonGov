import psycopg2
import os
import random
from dotenv import load_dotenv

load_dotenv()

MIN_SIM = 0.6     # 0 to 1: how alike the two descriptions must be. Raise to be stricter.

MATCH_QUERY = f"""
WITH cand AS (
    SELECT o.award_id    AS old_id,
           o.vendor_name AS old_vendor,
           o.end_date    AS old_end,
           o.description AS old_desc,
           n.award_id    AS next_id,
           n.vendor_name AS next_vendor,
           n.start_date  AS next_start,
           n.description AS next_desc,
           (o.vendor_uei = n.vendor_uei) AS retained,
           ABS(n.start_date - o.end_date) AS gap_days,
           similarity(regexp_replace(COALESCE(o.description,''), '^[0-9]+!', ''),
                      regexp_replace(COALESCE(n.description,''), '^[0-9]+!', '')) AS sim
    FROM award_history o
    JOIN award_history n
      ON  n.awarding_sub_agency = o.awarding_sub_agency
      AND n.naics_code          = o.naics_code
      AND n.psc_code            = o.psc_code
      AND LEFT(split_part(n.award_id, '_', 3), 6)
        = LEFT(split_part(o.award_id, '_', 3), 6)
      AND n.start_date BETWEEN o.end_date - 30 AND o.end_date + 365
      AND n.award_id <> o.award_id
    WHERE o.total_value > 250000
      AND o.award_id LIKE '%-NONE-%-NONE-'
      AND n.award_id LIKE '%-NONE-%-NONE-'
      AND o.vendor_uei IS NOT NULL
      AND n.vendor_uei IS NOT NULL
      AND o.end_date >= '2014-10-01'
      AND o.end_date <= (SELECT MAX(start_date) FROM award_history) - 365
      AND similarity(regexp_replace(COALESCE(o.description,''), '^[0-9]+!', ''),
                     regexp_replace(COALESCE(n.description,''), '^[0-9]+!', '')) >= {MIN_SIM}
),
best AS (
    SELECT DISTINCT ON (old_id) *
    FROM cand
    ORDER BY old_id, sim DESC, gap_days
)
SELECT DISTINCT ON (next_id) *
FROM best
ORDER BY next_id, sim DESC, gap_days
"""

conn = None
try:
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=5432,
        database='poseidon',
        user='poseidon',
        password=os.environ.get("DB_PASSWORD"),
        sslmode='require',
        connect_timeout=10
    )
    print("✅ Connected to RDS!")
    cur = conn.cursor()

    # one-time: turn on the text-similarity feature
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.commit()

    cur.execute(MATCH_QUERY)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()

    if not rows:
        print("\nNo matched pairs. Try lowering MIN_SIM to 0.3.")
    else:
        kept = sum(1 for r in rows if r["retained"])
        print(f"\n🔗 {len(rows)} matched pairs, {kept} kept ({kept / len(rows):.0%})")
        print("Random sample of 20:\n")
        for r in random.sample(rows, min(20, len(rows))):
            label = "KEPT" if r["retained"] else "LOST"
            print(f"[{label}]  similarity {float(r['sim']):.2f}   gap {r['gap_days']} days")
            print(f"  OLD: {r['old_vendor']}  (ended {r['old_end']})")
            print(f"       {(r['old_desc'] or '')[:90]}")
            print(f"  NEW: {r['next_vendor']}  (started {r['next_start']})")
            print(f"       {(r['next_desc'] or '')[:90]}")
            print()

except Exception as e:
    print(f"Database error: {e}")
    raise
finally:
    if conn:
        conn.close()