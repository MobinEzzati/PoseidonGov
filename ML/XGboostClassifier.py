from xgboost import XGBClassifier
import  os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score 

DB_URL = os.environ["DATABASE_URL"]

conn = None
try:
    conn = psycopg2.connect(
        host=DB_URL,
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
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = %s;
""",
    ("entity",),
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



def featureEngineering ():
    