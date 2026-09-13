import psycopg2
import os

conn = psycopg2.connect(
    host="poseidongov-db.cf6s0y8eqhz4.us-east-1.rds.amazonaws.com",
    port=5432,
    dbname="poseidon",
    user="poseidon",
    password=os.environ.get("DB_PASSWORD"),
    sslmode="require"
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
"""

cur.execute(schema)
conn.commit()
print("✅ Schema applied!")
cur.close()
conn.close()