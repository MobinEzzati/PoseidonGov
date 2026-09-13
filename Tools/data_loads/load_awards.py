import json
import psycopg2
import os
from dotenv import load_dotenv
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

    with open("/Users/mobinezzati/Desktop/Portfolios/AIMLProjects/PoseidonGov/ingestion/clients/awards_raw.json") as f:
        awards = json.load(f)
    print(f"Loaded {len(awards)} awards from file")

    inserted = 0
    for a in awards:
        cur.execute(
            """
            INSERT INTO award (award_id, recipient_name, amount,
                               awarding_agency, awarding_sub_agency, naics_code, pop_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (award_id) DO UPDATE SET pop_end = EXCLUDED.pop_end
            """,
            (
                a.get("Award ID"),
                a.get("Recipient Name"),
                a.get("Award Amount"),
                a.get("Awarding Agency"),
                a.get("Awarding Sub Agency"),
                a.get("NAICS Code"),
                a.get("End Date"),
            ),
        )
        inserted += cur.rowcount

    conn.commit()
    print(f"Inserted {inserted} new rows")

    cur.execute("SELECT count(*) FROM award")
    total = cur.fetchone()[0]
    print(f"Table now has {total} total rows")

except Exception as error:
    print("Error:", error)

finally:
    if conn:
        cur.close()
        conn.close()
    print("Connection closed.")