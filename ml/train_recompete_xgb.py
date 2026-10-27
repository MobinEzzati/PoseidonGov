"""
train_recompete_xgb.py

Trains an XGBoost model to predict whether a contract's incumbent vendor
KEEPS the follow-on work (retained = True) or LOSES it (retained = False).

Reads the labeled pairs from recompete_training, pulls features from
award_history, does a TIME-BASED split (train on older contracts, test on
newer ones), trains the model, and compares it against a dumb baseline.
The reported metrics come from that hold-out test. The saved model is then
refit on ALL labeled pairs, since the hold-out has already done its job.

Run:  python -m ml.train_recompete_xgb
"""

import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from xgboost import XGBClassifier

from app.db import get_db
from ml.recompete_features import CATEGORICAL, FEATURES, NUMERIC, build_features

# ---------- settings (change these, not the code below) ----------
MIN_CONF      = 0.6     # only train on pairs at/above this match confidence (raise to 0.8 for cleaner labels, fewer rows)
TEST_FRAC     = 0.20    # newest 20% of contracts become the test set
MODEL_VERSION = "recompete_xgb_v1"
MODEL_PATH    = f"models/{MODEL_VERSION}.json"

QUERY = """
SELECT t.retained,
       t.value_usd,
       t.duration_days,
       o.award_id,
       o.awarding_sub_agency,
       o.naics_code,
       o.psc_code,
       o.end_date
FROM recompete_training t
JOIN award_history o ON o.award_id = t.old_award_id
WHERE t.match_confidence >= %s
  AND t.value_usd IS NOT NULL
  AND o.end_date IS NOT NULL
"""


def make_model(y_train):
    # scale_pos_weight balances the two classes so the model doesn't just
    # predict the majority. max_depth=3 keeps it simple so it won't memorize.
    neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
    return XGBClassifier(
        max_depth=3,
        learning_rate=0.05,
        n_estimators=300,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=neg / max(pos, 1),
        enable_categorical=True,
        tree_method="hist",
        eval_metric="logloss",
        random_state=0,
    )


def main():
    # ---------- 1. load the labeled data ----------
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(QUERY, (MIN_CONF,))
        df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    conn.close()

    print(f"Loaded {len(df)} labeled pairs")
    if len(df) < 50:
        print("Too few rows to train. Load more data, then rerun.")
        raise SystemExit

    kept_rate = df["retained"].mean()
    print(f"Base rate: {kept_rate:.0%} of incumbents kept the work\n")

    # ---------- 2. build features ----------
    X = build_features(df)
    y = df["retained"].astype(int)

    # ---------- 3. time-based split (NOT random) ----------
    # Sort by when the old contract ended; train on the past, test on the future.
    # This mimics real use: predict new recompetes from old ones.
    order = df["end_date"].argsort().to_numpy()
    cut = int(len(df) * (1 - TEST_FRAC))
    train_idx, test_idx = order[:cut], order[cut:]

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    print(f"Train: {len(X_train)} rows  |  Test: {len(X_test)} rows")
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        print("One split has only a single class (all kept or all lost). "
              "Need more data for a meaningful test. Stopping.")
        raise SystemExit

    # ---------- 4. train ----------
    model = make_model(y_train)
    model.fit(X_train, y_train)

    # ---------- 5. evaluate vs a dumb baseline ----------
    proba = model.predict_proba(X_test)[:, 1]

    # Baseline = ignore all features, always guess the training base rate.
    baseline = np.full(len(y_test), y_train.mean())

    auc   = roc_auc_score(y_test, proba)
    ap    = average_precision_score(y_test, proba)
    brier = brier_score_loss(y_test, proba)
    brier_base = brier_score_loss(y_test, baseline)

    print("\n================ RESULTS ================")
    print(f"AUC                : {auc:.3f}   (0.5 = coin flip, 1.0 = perfect)")
    print(f"Avg precision      : {ap:.3f}   (base rate = {y_test.mean():.3f})")
    print(f"Brier (model)      : {brier:.3f}   (lower is better)")
    print(f"Brier (dumb guess) : {brier_base:.3f}")
    if brier < brier_base:
        print(">> Model beats the dumb baseline. The features carry real signal.")
    else:
        print(">> Model does NOT beat the baseline yet. Likely need more data or features.")
    print("=========================================\n")

    # ---------- 6. what mattered ----------
    importances = model.get_booster().get_score(importance_type="gain")
    if importances:
        print("Feature importance (gain):")
        for feat, score in sorted(importances.items(), key=lambda x: -x[1]):
            print(f"  {feat:25s} {score:8.1f}")

    # ---------- 7. refit on everything and save ----------
    final = make_model(y)
    final.fit(X, y)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    final.save_model(MODEL_PATH)
    meta = {
        "model_version": MODEL_VERSION,
        "rows": int(len(df)),
        "base_rate": float(kept_rate),
        "min_confidence": MIN_CONF,
        "test_fraction": TEST_FRAC,
        "metrics_from": "hold-out test; saved model is refit on all rows",
        "auc": float(auc),
        "avg_precision": float(ap),
        "brier": float(brier),
        "brier_baseline": float(brier_base),
        "features_numeric": NUMERIC,
        "features_categorical": CATEGORICAL,
        "feature_order": FEATURES,
        # exact category lists, in order, so serving encodes values identically
        "categories": {c: [str(v) for v in X[c].cat.categories] for c in CATEGORICAL},
    }
    with open(MODEL_PATH.replace(".json", "_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metrics to {MODEL_PATH.replace('.json', '_meta.json')}")


if __name__ == "__main__":
    main()
