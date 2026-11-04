
import numpy as np 
import pandas as pd 
from ml.train_recompete_xgb import make_model,QUERY,MIN_CONF
from app.db import get_db
from datetime import datetime





def main ():
    conn = get_db()
    with conn.cursor() as cur:
            cur.execute(QUERY, (MIN_CONF,))
            df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
            df["end_date"] = pd.to_datetime(df["end_date"])
            filtered_df = df[df['end_date'].between('2020-01-01', '2025-01-01')]
            
            
    conn.close()

    print(filtered_df.head(10))


if __name__ == "__main__":
    main()
    