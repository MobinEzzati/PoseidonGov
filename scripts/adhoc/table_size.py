from app.db import get_db
import json
import os

QUERY = """
SELECT relname AS table_name,
       pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
       n_live_tup AS approx_rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
"""
def main():


    conn = get_db()
    with conn.cursor() as cur:


        cur.execute(QUERY)
        res = cur.fetchall() 
        print(res)
    conn.close()




if __name__ == "__main__":
    main()
