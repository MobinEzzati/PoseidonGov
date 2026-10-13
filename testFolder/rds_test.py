import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = None
try:
    conn = psycopg2.connect(
        host='poseidongov-db.cf6s0y8eqhz4.us-east-1.rds.amazonaws.com',
        port=5432,
        database='poseidon',
        user='poseidon',
        password=os.environ.get("DB_PASSWORD"),
        sslmode='require',
        connect_timeout=10
    )
    print("✅ Connected to RDS!")
    cur = conn.cursor()

    # 1. Tables + row counts
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [t[0] for t in cur.fetchall()]
    print("\n📋 Tables and row counts:")
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        print(f"  {t}: {cur.fetchone()[0]}")

    # # 2. risk_score with column names
    # cur.execute("SELECT * FROM risk_score LIMIT 20")
    # col_names = [d[0] for d in cur.description]
    # rows = cur.fetchall()
    # print("\n🎯 risk_score columns:", col_names)
    # for row in rows:
    #     print(row)

    cur.close()
except Exception as e:
    print(f"Database error: {e}")
    raise
finally:
    if conn:
        conn.close()
