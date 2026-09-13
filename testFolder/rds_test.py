import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

try:
    conn = psycopg2.connect(
        host="poseidongov-db.cf6s0y8eqhz4.us-east-1.rds.amazonaws.com",
        port=5432,
        dbname="postgres",
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10
    )
    print("✅ Connected to RDS!")
    conn.close()
except Exception as e:
    print(f"❌ Failed: {e}")