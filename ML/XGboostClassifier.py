"""
train_recompete_xgb.py

Trains an XGBoost model to predict whether a contract's incumbent vendor
KEEPS the follow-on work (retained = True) or LOSES it (retained = False).

Reads the labeled pairs from recompete_training, pulls features from
award_history, does a TIME-BASED split (train on older contracts, test on
newer ones), trains the model, and compares it against a dumb baseline.

Run:  python train_recompete_xgb.py
Needs: pip install xgboost scikit-learn pandas psycopg2-binary python-dotenv
"""

import os
import json
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from xgboost import XGBClassifier

load_dotenv()

# ---------- settings (change these, not the code below) ----------
MIN_CONF   = 0.6     # only train on pairs at/above this match confidence (raise to 0.8 for cleaner labels, fewer rows)
TEST_FRAC  = 0.20    # newest 20% of contracts become the test set
MODEL_PATH = "models/recompete_xgb_v1.json"

# These columns from award_history become the model's inputs.
CATEGORICAL = ["awarding_sub_agency", "naics_code", "psc_code", "office"]
NUMERIC     = ["log_value", "duration_days"]

# ---------- 1. load the labeled data ----------
conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=5432, database='poseidon', user='poseidon',
    password=os.environ["DB_PASSWORD"], sslmode='require', connect_timeout=10,
)

QUERY = f"""
SELECT t.retained,
       t.value_usd,
       t.duration_days,
       o.awarding_sub_agency,
       o.naics_code,
       o.psc_code,
       o.end_date,
       LEFT(split_part(o.award_id, '_', 3), 6) AS office
FROM recompete_training t
JOIN award_history o ON o.award_id = t.old_award_id
WHERE t.match_confidence >= {MIN_CONF}
  AND t.value_usd IS NOT NULL
  AND o.end_date IS NOT NULL
"""

df = pd.read_sql(QUERY, conn)
conn.close()

print(f"Loaded {len(df)} labeled pairs")
if len(df) < 50:
    print("Too few rows to train. Load more data, then rerun.")
    raise SystemExit

kept_rate = df["retained"].mean()
print(f"Base rate: {kept_rate:.0%} of incumbents kept the work\n")

# ---------- 2. build features ----------
df["log_value"] = np.log1p(df["value_usd"].astype(float))
df["duration_days"] = df["duration_days"].fillna(0).astype(float)
for c in CATEGORICAL:
    df[c] = df[c].fillna("UNKNOWN").astype("category")

y = df["retained"].astype(int)
X = df[NUMERIC + CATEGORICAL]

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
# scale_pos_weight balances the two classes so the model doesn't just
# predict the majority. max_depth=3 keeps it simple so it won't memorize.
neg, pos = (y_train == 0).sum(), (y_train == 1).sum()
model = XGBClassifier(
    max_depth=3,
    learning_rate=0.05,
    n_estimators=300,
    subsample=0.9,
    colsample_bytree=0.9,
    scale_pos_weight=neg / max(pos, 1),
    enable_categorical=True,
    tree_method="hist",
    eval_metric="logloss",
)
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

# ---------- 7. save ----------
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
model.save_model(MODEL_PATH)
meta = {
    "rows": int(len(df)),
    "base_rate": float(kept_rate),
    "min_confidence": MIN_CONF,
    "test_fraction": TEST_FRAC,
    "auc": float(auc),
    "avg_precision": float(ap),
    "brier": float(brier),
    "brier_baseline": float(brier_base),
    "features_numeric": NUMERIC,
    "features_categorical": CATEGORICAL,
}
with open(MODEL_PATH.replace(".json", "_meta.json"), "w") as f:
    json.dump(meta, f, indent=2)

print(f"Saved model to {MODEL_PATH}")
print(f"Saved metrics to {MODEL_PATH.replace('.json', '_meta.json')}")