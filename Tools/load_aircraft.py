import json
import psycopg2
import pandas as pd 


# with open("/Users/mobinezzati/Desktop/Portfolios/AIMLProjects/PoseidonGov/ingestion/clients/ReleasableAircraft/MASTER.txt") as f:

#     df = pd.read_csv(f)
#     print(f"Loaded {len(df)} awards from file")
#     print(df.columns)

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

    with open("/Users/mobinezzati/Desktop/Portfolios/AIMLProjects/PoseidonGov/ingestion/clients/ReleasableAircraft/MASTER.txt") as f:
        airCrafts = pd.read_csv(f, dtype=str)
        airCrafts.columns = airCrafts.columns.str.strip()
        print(f"Loaded {len(airCrafts)} awards from file")

    inserted = 0
    for _,a in airCrafts.iterrows():
        year = int(a["YEAR MFR"].strip()) if a["YEAR MFR"].strip() else None
        

        cur.execute(
            """
            INSERT INTO aircraft (n_number, owner_name, make_model, year_mfr, owner_uei)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (n_number) DO NOTHING
            """,
            (
                a.get("N-NUMBER"),
                a.get("NAME"),
                a.get("MFR MDL CODE"),
                year,
                None,
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