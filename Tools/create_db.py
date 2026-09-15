import psycopg2

import os

conn = psycopg2.connect(
    host="poseidongov-db.cf6s0y8eqhz4.us-east-1.rds.amazonaws.com",
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