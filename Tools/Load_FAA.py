import json
import psycopg2

conn = None
try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="poseidon",
        user="poseidon",
        password="localdev",
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
                               awarding_agency, awarding_sub_agency, naics_code)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (award_id) DO NOTHING
            """,
            (
                a.get("Award ID"),
                a.get("Recipient Name"),
                a.get("Award Amount"),
                a.get("Awarding Agency"),
                a.get("Awarding Sub Agency"),
                a.get("NAICS Code"),
            ),
        )
        inserted += cur.rowcount

    conn.commit()                          # SAVE — must come before any close
    print(f"Inserted {inserted} new rows")

    cur.execute("SELECT count(*) FROM award")   # run the query

    total = cur.fetchone()[0]                    # THEN read one result
    print(f"Table now has {total} total rows")

except Exception as error:
    print("Error:", error)

finally:
    if conn:
        cur.close()
        conn.close()
    print("Connection closed.")