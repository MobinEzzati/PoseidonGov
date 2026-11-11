import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from app.db import get_db
from ml.recompete_features import build_features
from ml.train_recompete_xgb import MIN_CONF, QUERY, make_model

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


def evaluate_year(X, y, train_mask, test_mask, test_year) -> dict | None:
    """Train on earlier years, test on one year. Returns None if a split has one class."""
    X_train, X_test = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]

    if y_train.nunique() < 2 or y_test.nunique() < 2:
        print(f"{test_year}: skipped (only one class in train or test)")
        return None

    model = make_model(y_train)
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]          # P(retained)

    baseline = np.full(len(y_test), y_train.mean())   # always guess the training rate

    return {
        "year": test_year,
        "n_train": len(y_train),
        "n_test": len(y_test),
        "test_kept_rate": round(y_test.mean(), 3),
        "auc": roc_auc_score(y_test, proba),
        "avg_precision": average_precision_score(y_test, proba),
        "brier": brier_score_loss(y_test, proba),
        "brier_baseline": brier_score_loss(y_test, baseline),
    }


def main():
    df = load_pairs()
    print(f"Loaded {len(df)} pairs\n")

    X = build_features(df)
    y = df["retained"].astype(int)

    results = []
    for test_year in TEST_YEARS:
        train_mask = df["year"] < test_year
        test_mask = df["year"] == test_year
        row = evaluate_year(X, y, train_mask, test_mask, test_year)
        if row is not None:
            results.append(row)

    table = pd.DataFrame(results)
    table["beats_baseline"] = table["brier"] < table["brier_baseline"]

    print(table.round(3).to_string(index=False))
    print("\nSummary across years:")
    print(table[["auc", "brier", "brier_baseline"]].agg(["mean", "min", "max"]).round(3))
    print(f"\nModel beat the baseline in {table['beats_baseline'].sum()} of {len(table)} years")


if __name__ == "__main__":
    main()