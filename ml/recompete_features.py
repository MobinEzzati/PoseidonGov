"""
Feature building shared by training (ml.train_recompete_xgb) and serving
(ml.recompete_model). Keep all feature logic here so the two cannot drift.
"""

import numpy as np
import pandas as pd

CATEGORICAL = ["awarding_sub_agency", "naics_code", "psc_code", "office"]
NUMERIC = ["log_value", "duration_days"]
FEATURES = NUMERIC + CATEGORICAL
UNKNOWN = "UNKNOWN"


def office_from_award_id(award_id) -> str:
    # CONT_AWD_<piid>_<agency>_... -> first 6 chars of the piid (the contracting office)
    parts = str(award_id).split("_")
    return parts[2][:6] if len(parts) > 2 else ""


def build_features(df: pd.DataFrame, categories: dict | None = None) -> pd.DataFrame:
    """df needs: value_usd, duration_days, awarding_sub_agency, naics_code,
    psc_code, award_id.

    categories=None (training): categories are taken from df.
    categories=dict (serving): the category lists saved at training time, in
    the same order; values not seen in training become missing, which XGBoost
    handles natively.
    """
    X = pd.DataFrame(index=df.index)
    X["log_value"] = np.log1p(df["value_usd"].astype(float))
    X["duration_days"] = df["duration_days"].fillna(0).astype(float)

    source = df.assign(office=df["award_id"].map(office_from_award_id))
    for col in CATEGORICAL:
        values = source[col].fillna(UNKNOWN)
        if categories is None:
            X[col] = values.astype("category")
        else:
            known = values.where(values.isin(categories[col]))
            X[col] = pd.Categorical(known, categories=categories[col])
    return X[FEATURES]
