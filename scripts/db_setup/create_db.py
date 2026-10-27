import psycopg2

import os

conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=5432,
    dbname="postgres",
    user="poseidon",
    password=os.environ.get("DB_PASSWORD"),
    sslmode="require"
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("CREATE DATABASE poseidon;")
print("✅ Database created!")
cur.close()
conn.close()