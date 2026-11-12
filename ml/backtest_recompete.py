"""
backtest_recompete.py

Evaluates the recompete model two ways:
1. Yearly backtest: for each test year, train on earlier years (purged so every
   training label was known before the test year began) and test on that year.
2. Random 80/20 splits (5 seeds), for comparison.

Does not save a model. Run:  python -m ml.backtest_recompete
"""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from app.db import get_db
from ml.recompete_features import build_features
from ml.train_recompete_xgb import MIN_CONF, make_model

TEST_YEARS = range(2020, 2026)   # 2020, 2021, ..., 2025
PURGE = True

BACK_TEST_QUERY = """
SELECT t.retained,
       t.value_usd,
       t.duration_days,
       o.award_id,
       o.awarding_sub_agency,
       o.naics_code,
       o.psc_code,
       o.end_date,
       n.start_date AS next_start_date
FROM recompete_training t
JOIN award_history o ON o.award_id = t.old_award_id
JOIN award_history n ON n.award_id = t.next_award_id
WHERE t.match_confidence >= %s
  AND t.value_usd IS NOT NULL
  AND o.end_date IS NOT NULL
ORDER BY t.old_award_id
"""


def load_pairs() -> pd.DataFrame:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(BACK_TEST_QUERY, (MIN_CONF,))
        df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    conn.close()

    df["end_date"] = pd.to_datetime(df["end_date"])
    df["next_start_date"] = pd.to_datetime(df["next_start_date"])
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


def random_split_eval(X, y) -> list[dict]:
    """Random 80/20 splits (5 seeds) for comparison with the time-based backtest."""
    results = []
    for seed in range(5):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=seed
        )
        model = make_model(y_train)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]          # P(retained)

        baseline = np.full(len(y_test), y_train.mean())   # always guess the training rate

        results.append({
            "seed": seed,
            "n_train": len(y_train),
            "n_test": len(y_test),
            "auc": roc_auc_score(y_test, proba),
            "avg_precision": average_precision_score(y_test, proba),
            "brier": brier_score_loss(y_test, proba),
            "brier_baseline": brier_score_loss(y_test, baseline),
        })
    return results


def main():
    df = load_pairs()
    print(f"Loaded {len(df)} pairs")
    print(f"Purge: {'ON' if PURGE else 'OFF'}\n")

    X = build_features(df)
    y = df["retained"].astype(int)

    results = []
    for test_year in TEST_YEARS:
        train_mask = df["year"] < test_year
        if PURGE:
            # Only train on pairs whose outcome was known before the test year began
            year_start = pd.Timestamp(test_year, 1, 1)
            train_mask = train_mask & (df["next_start_date"] < year_start)
        test_mask = df["year"] == test_year
        row = evaluate_year(X, y, train_mask, test_mask, test_year)
        if row is not None:
            results.append(row)

    table = pd.DataFrame(results)
    table["beats_baseline"] = table["brier"] < table["brier_baseline"]

    print("================ YEARLY BACKTEST ================")
    print(table.round(3).to_string(index=False))
    print("\nSummary across years:")
    print(table[["auc", "brier", "brier_baseline"]].agg(["mean", "min", "max"]).round(3))
    print(f"\nModel beat the baseline in {table['beats_baseline'].sum()} of {len(table)} years")

    print("\n================ RANDOM SPLIT (for comparison) ================")
    random_table = pd.DataFrame(random_split_eval(X, y))
    print(random_table.round(3).to_string(index=False))
    print("\nSummary across seeds:")
    print(random_table[["auc", "brier", "brier_baseline"]].agg(["mean", "min", "max"]).round(3))


if __name__ == "__main__":
    main()