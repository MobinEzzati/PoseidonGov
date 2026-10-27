import psycopg2
import os
from dotenv import load_dotenv
load_dotenv() 

conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=5432,
    dbname="poseidon",
    user="poseidon",
    password=os.environ.get("DB_PASSWORD"),
    sslmode="require",
    connect_timeout=10,
)
cur = conn.cursor()

schema = """
CREATE TABLE IF NOT EXISTS aircraft (
    n_number text NOT NULL PRIMARY KEY,
    owner_name text,
    owner_uei text,
    make_model text,
    year_mfr integer
);

CREATE TABLE IF NOT EXISTS award (
    award_id text NOT NULL PRIMARY KEY,
    recipient_name text,
    amount numeric,
    awarding_agency text,
    awarding_sub_agency text,
    naics_code text,
    ingested_at timestamp with time zone DEFAULT now(),
    pop_end date
);

CREATE TABLE IF NOT EXISTS entity (
    uei text NOT NULL PRIMARY KEY,
    name text NOT NULL,
    naics_primary text,
    state text,
    first_seen date,
    last_seen date
);

CREATE TABLE IF NOT EXISTS opportunity (
    notice_id text NOT NULL PRIMARY KEY,
    title text,
    agency text,
    naics_code text,
    posted_date date,
    response_deadline date,
    description text
);

CREATE TABLE IF NOT EXISTS risk_score (
    recipient_name text NOT NULL,
    as_of date NOT NULL,
    hhi_agency numeric,
    top_customer_pct numeric,
    recompete_risk numeric,
    anomaly_flag boolean,
    PRIMARY KEY (recipient_name, as_of)
);

-- ===== NEW: historical data for training the recompete model =====

CREATE TABLE IF NOT EXISTS award_history (
    award_id         text PRIMARY KEY,
    vendor_name      text,
    vendor_uei       text,
    awarding_agency  text,
    awarding_sub_agency text,
    naics_code       text,
    psc_code         text,
    description      text,
    start_date       date,
    end_date         date,
    total_value      numeric,
    extent_competed  text,
    offers_received  integer,
    set_aside_type   text,
    ingested_at      timestamp with time zone DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recompete_training (
    old_award_id        text PRIMARY KEY REFERENCES award_history(award_id),
    next_award_id       text,
    retained            boolean,
    match_confidence    numeric,
    value_usd           numeric,
    duration_days       integer,
    was_sole_source     boolean,
    offers_received     integer,
    agency_vendor_share numeric
);

CREATE INDEX IF NOT EXISTS idx_award_history_end_date
    ON award_history (end_date);
CREATE INDEX IF NOT EXISTS idx_award_history_match
    ON award_history (awarding_agency, naics_code, start_date);

-- optional: track which method produced a score
ALTER TABLE risk_score ADD COLUMN IF NOT EXISTS model_version text;
"""

try:
    cur.execute(schema)
    conn.commit()
    print("✅ Schema applied!")
except Exception as e:
    conn.rollback()
    print(f"❌ Failed: {e}")
    raise
finally:
    cur.close()
    conn.close()