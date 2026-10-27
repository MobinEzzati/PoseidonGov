"""
Serves the XGBoost recompete model. The model predicts the chance the
incumbent KEEPS a contract; risk = 1 - that chance. Returns None whenever the
model can't be used so callers fall back to the rule-based score.
"""

import json
import logging
import os
from pathlib import Path

import pandas as pd

from ml.recompete_features import build_features, office_from_award_id

logger = logging.getLogger("poseidongov")

MODEL_PATH = Path(os.environ.get(
    "RECOMPETE_MODEL_PATH",
    Path(__file__).resolve().parents[1] / "models" / "recompete_xgb_v1.json",
))
WINDOW_MONTHS = 24    # only contracts ending within this window count as recompete exposure

# The model only knows the NAICS codes and contracting offices it was trained
# on. Unfamiliar contracts come out with a misleadingly low risk, so require
# this share of a company's exposure (by value) to be familiar, else fall back.
MIN_COVERAGE = 0.70

# Label cutoffs for the model's risk score (value-weighted mean of 1 - P(kept)).
# These are terciles of the scores of the companies the model covers, so the
# labels rank companies against each other; they are not probabilities and not
# the rule-based 0.4 / 0.7 cutoffs.
HIGH_CUTOFF = 0.23
MEDIUM_CUTOFF = 0.07

_cache = {}


def interpret_recompete_model(score: float) -> str:
    if score > HIGH_CUTOFF:
        return "HIGH"
    elif score > MEDIUM_CUTOFF:
        return "MEDIUM"
    else:
        return "LOW"


def _load():
    if "loaded" not in _cache:
        try:
            from xgboost import XGBClassifier
            meta = json.loads(MODEL_PATH.with_name(MODEL_PATH.stem + "_meta.json").read_text())
            model = XGBClassifier()
            model.load_model(str(MODEL_PATH))
            _cache["loaded"] = (model, meta)
        except Exception:
            logger.warning("Recompete model unavailable, using rule-based fallback", exc_info=True)
            _cache["loaded"] = None
    return _cache["loaded"]


def score_company(cur, company_name: str):
    """Returns {"score", "method", "model_version", "contracts_scored"}, or
    None if the model isn't available, we have no contract history for the
    company, or too little of its exposure is familiar to the model (so the
    caller should fall back)."""
    loaded = _load()
    if loaded is None:
        return None
    model, meta = loaded

    cur.execute(
        "SELECT 1 FROM award_history WHERE vendor_name = %s LIMIT 1",
        (company_name,),
    )
    if cur.fetchone() is None:
        return None

    cur.execute("""
        SELECT award_id, awarding_sub_agency, naics_code, psc_code,
               total_value AS value_usd, (end_date - start_date) AS duration_days
        FROM award_history
        WHERE vendor_name = %s
          AND total_value > 0
          AND end_date BETWEEN CURRENT_DATE
                           AND CURRENT_DATE + make_interval(months => %s)
    """, (company_name, WINDOW_MONTHS))
    rows = cur.fetchall()

    result = {
        "method": "xgboost",
        "model_version": meta["model_version"],
        "contracts_scored": len(rows),
    }
    if not rows:
        return {**result, "score": 0.0}

    df = pd.DataFrame(rows, columns=[d[0] for d in cur.description])
    weights = df["value_usd"].astype(float)

    known = (
        df["naics_code"].isin(meta["categories"]["naics_code"])
        & df["award_id"].map(office_from_award_id).isin(meta["categories"]["office"])
    )
    if weights[known].sum() / weights.sum() < MIN_COVERAGE:
        return None

    X = build_features(df, meta["categories"])
    risk = 1.0 - model.predict_proba(X)[:, 1]
    return {**result, "score": float((risk * weights).sum() / weights.sum())}
