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
    print("✅ Connected to RDS!"
          )
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = cur.fetchall() 
    print("📋 Tables:", tables)

    cur.execute(
    """
    select * from risk_score
    limit 20
"""
    )

    columns = cur.fetchall() 

    for column in columns : 
        print(column)

    


    cur.close()
except Exception as e:
    print(f"Database error: {e}")
    raise
finally:
    if conn:
        conn.close()
