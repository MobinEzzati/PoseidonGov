import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_values
load_dotenv()

conn = None
try:
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=5432,
        dbname="poseidon",
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        sslmode="require"
    )
    cur = conn.cursor()

    with open("/Users/mobinezzati/Desktop/Portfolios/AIMLProjects/PoseidonGov/Tools/ReleasableAircraft/MASTER.txt") as f:
        airCrafts = pd.read_csv(f, dtype=str)
        airCrafts.columns = airCrafts.columns.str.strip()
        print(f"Loaded {len(airCrafts)} aircraft from file")

    batch = []
    for _, a in airCrafts.iterrows():
        year_raw = str(a.get("YEAR MFR", "")).strip()
        year = int(year_raw) if year_raw.isdigit() else None
        batch.append((
            a.get("N-NUMBER"),
            a.get("NAME"),
            a.get("MFR MDL CODE"),
            year,
            None,
        ))

    print("Inserting batch...")
    execute_values(cur, """
        INSERT INTO aircraft (n_number, owner_name, make_model, year_mfr, owner_uei)
        VALUES %s
        ON CONFLICT (n_number) DO NOTHING
    """, batch, page_size=1000)

    conn.commit()
    print(f"Inserted {len(batch)} rows")

    cur.execute("SELECT count(*) FROM aircraft")
    print(f"Aircraft table now has {cur.fetchone()[0]} rows")

except Exception as error:
    print("Error:", error)

finally:
    if conn:
        cur.close()
        conn.close()
    print("Connection closed.")