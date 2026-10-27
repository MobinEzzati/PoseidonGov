import psycopg2
import os
from dotenv import load_dotenv
from datetime import date, timedelta


load_dotenv()

# ---------- settings (change these, not the SQL) ----------
MIN_VALUE = 250000   # ignore old contracts smaller than this ($)
MIN_SIM   = 0.6      # how alike the descriptions must be (0 to 1)
GAP_BEFORE = 30      # new contract may start this many days BEFORE the old one ended
GAP_AFTER  = 365     # ...or up to this many days AFTER
SHOW_SAMPLE = True   # print 3 example rows after each step
DATA_ENDS = date(2026, 9, 30)

LABEL_CUTOFF = DATA_ENDS - timedelta(days=GAP_AFTER)
# Used in two places, so defined once: strip the leading item number like "8501781762!"
def clean(col):
    return f"regexp_replace(COALESCE({col},''), '^[0-9]+!', '')"

# ---------- the steps, in order ----------
STEPS = []

# STEP 1: every possible old->new pair that follows the basic rules
STEPS.append(("1. candidate pairs (same office, agency, NAICS, PSC, timing)", f"""
CREATE TEMP TABLE s1_candidates AS
SELECT o.award_id AS old_id,
       n.award_id AS next_id,
       (o.vendor_uei = n.vendor_uei)       AS retained,
       ABS(n.start_date - o.end_date)      AS gap_days,
       similarity({clean('o.description')}, {clean('n.description')}) AS sim
FROM award_history o
JOIN award_history n
  ON  n.awarding_sub_agency = o.awarding_sub_agency
  AND n.naics_code          = o.naics_code
  AND n.psc_code            = o.psc_code
  AND LEFT(split_part(n.award_id,'_',3),6) = LEFT(split_part(o.award_id,'_',3),6)
  AND n.start_date BETWEEN o.end_date - {GAP_BEFORE} AND o.end_date + {GAP_AFTER}
  AND n.award_id <> o.award_id
WHERE o.total_value > {MIN_VALUE}
  AND n.total_value > {MIN_VALUE}
  AND o.award_id LIKE '%-NONE-%-NONE-'
  AND n.award_id LIKE '%-NONE-%-NONE-'
  AND o.vendor_uei IS NOT NULL
  AND n.vendor_uei IS NOT NULL
  AND o.end_date >= '2014-10-01'
  AND o.end_date <= DATE '{LABEL_CUTOFF}'
""", "s1_candidates"))

print(f"Labeling contracts that ended {'2014-10-01'} to {LABEL_CUTOFF} (data ends {DATA_ENDS})")

# STEP 2: keep only pairs whose descriptions are alike
STEPS.append((f"2. similar descriptions (sim >= {MIN_SIM})", f"""
CREATE TEMP TABLE s2_similar AS
SELECT * FROM s1_candidates WHERE sim >= {MIN_SIM}
""", "s2_similar"))

# STEP 3: each old contract gets only its single best follow-on
STEPS.append(("3. one follow-on per old contract", """
CREATE TEMP TABLE s3_one_per_old AS
SELECT DISTINCT ON (old_id) *
FROM s2_similar
ORDER BY old_id, sim DESC, gap_days
""", "s3_one_per_old"))

# STEP 4: each new contract can only be claimed by one old contract
STEPS.append(("4. one old contract per follow-on", """
CREATE TEMP TABLE s4_final AS
SELECT DISTINCT ON (next_id) *
FROM s3_one_per_old
ORDER BY next_id, sim DESC, gap_days
""", "s4_final"))

# STEP 5: save into the real table
SAVE_SQL = """
INSERT INTO recompete_training
    (old_award_id, next_award_id, retained, match_confidence, value_usd, duration_days)
SELECT f.old_id, f.next_id, f.retained, f.sim, o.total_value, (o.end_date - o.start_date)
FROM s4_final f
JOIN award_history o ON o.award_id = f.old_id
ON CONFLICT (old_award_id) DO UPDATE SET
    next_award_id    = EXCLUDED.next_award_id,
    retained         = EXCLUDED.retained,
    match_confidence = EXCLUDED.match_confidence,
    value_usd        = EXCLUDED.value_usd,
    duration_days    = EXCLUDED.duration_days
"""

conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=5432, database='poseidon', user='poseidon',
    password=os.environ.get("DB_PASSWORD"), sslmode='require', connect_timeout=10
)
try:
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    for title, sql, table in STEPS:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        cur.execute(sql)
        cur.execute(f"SELECT COUNT(*), COALESCE(SUM(retained::int),0) FROM {table}")
        total, kept = cur.fetchone()
        pct = f"{kept/total:.0%}" if total else "n/a"
        print(f"STEP {title}: {total} rows, {kept} kept ({pct})")
        if SHOW_SAMPLE and total:
            cur.execute(f"SELECT old_id, next_id, retained, round(sim::numeric,2) FROM {table} LIMIT 3")
            for r in cur.fetchall():
                print("     ", r)

    cur.execute("DELETE FROM recompete_training WHERE old_award_id NOT IN (SELECT old_id FROM s4_final)")
    print(f"STEP 5a. removed {cur.rowcount} stale rows")

    cur.execute(SAVE_SQL)
    print(f"STEP 5b. saved/updated {cur.rowcount} rows")
    conn.commit()
finally:
    conn.close()