import pandas as pd

from app.db import get_db
from ml.train_recompete_xgb import MIN_CONF, QUERY

TEST_YEARS = range(2020, 2026)   # 2020, 2021, ..., 2025


def load_pairs() -> pd.DataFrame:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(QUERY, (MIN_CONF,))
        df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    conn.close()

    df["end_date"] = pd.to_datetime(df["end_date"])
    df["year"] = df["end_date"].dt.year
    return df


def main():
    df = load_pairs()
    print(f"Loaded {len(df)} pairs\n")

    for test_year in TEST_YEARS:
        train_mask = df["year"] < test_year
        test_mask = df["year"] == test_year
        print(f"{test_year}: train={train_mask.sum():4d}  test={test_mask.sum():3d}")


if __name__ == "__main__":
    main()