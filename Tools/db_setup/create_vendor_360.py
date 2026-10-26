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
CREATE OR REPLACE VIEW vendor_360 AS
WITH base AS (
    SELECT e.parent_group, h.vendor_uei, h.awarding_sub_agency AS agency,
           h.total_value, h.start_date, h.end_date
    FROM award_history h
    JOIN entity e ON e.uei = h.vendor_uei
    WHERE h.total_value IS NOT NULL
),
by_agency AS (
    SELECT parent_group, agency, SUM(total_value) AS v
    FROM base GROUP BY parent_group, agency
),
shares AS (
    SELECT parent_group, agency, v,
           v / NULLIF(SUM(v) OVER (PARTITION BY parent_group), 0) AS share
    FROM by_agency
),
agency_stats AS (
    SELECT parent_group,
           SUM(share * share)                      AS hhi_agency,
           MAX(share)                              AS top_agency_share,
           (array_agg(agency ORDER BY v DESC))[1]  AS top_agency
    FROM shares GROUP BY parent_group
),
totals AS (
    SELECT parent_group,
           COUNT(DISTINCT vendor_uei) AS n_ueis,
           COUNT(*)                   AS n_contracts,
           SUM(total_value)           AS total_value,
           MAX(total_value)           AS largest_contract,
           MIN(start_date)            AS first_start,
           MAX(start_date)            AS last_start
    FROM base GROUP BY parent_group
),
expiring AS (
    SELECT parent_group,
           COUNT(*)         AS n_expiring_18m,
           SUM(total_value) AS expiring_value
    FROM base
    WHERE end_date >= CURRENT_DATE
      AND end_date <  CURRENT_DATE + INTERVAL '18 months'
    GROUP BY parent_group
)
SELECT t.*,
       a.top_agency, a.top_agency_share, a.hhi_agency,
       COALESCE(x.n_expiring_18m, 0) AS n_expiring_18m,
       COALESCE(x.expiring_value, 0) AS expiring_value,
       COALESCE(x.expiring_value, 0) / NULLIF(t.total_value, 0) AS expiring_share
FROM totals t
JOIN agency_stats a USING (parent_group)
LEFT JOIN expiring x USING (parent_group)
""")
conn.commit()

cur.execute("""
    SELECT parent_group, n_contracts, ROUND(total_value/1e9, 1),
           top_agency, ROUND(top_agency_share::numeric, 2),
           ROUND(hhi_agency::numeric, 2), n_expiring_18m,
           ROUND(expiring_value/1e9, 1)
    FROM vendor_360
    WHERE parent_group IN ('LOCKHEED MARTIN','BOEING','RTX','NORTHROP GRUMMAN','GENERAL ELECTRIC')
    ORDER BY total_value DESC
""")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()