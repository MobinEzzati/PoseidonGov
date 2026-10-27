import json

import numpy as np
import pandas as pd
import pytest

from ml import recompete_model
from ml.recompete_features import FEATURES, build_features, office_from_award_id

CATEGORIES = {
    "awarding_sub_agency": ["Navy", "UNKNOWN"],
    "naics_code": ["336411"],
    "psc_code": ["1510"],
    "office": ["N00019"],
}


def contracts(**overrides):
    row = {
        "award_id": "CONT_AWD_N0001902C3002_9700_-NONE-_-NONE-",
        "awarding_sub_agency": "Navy",
        "naics_code": "336411",
        "psc_code": "1510",
        "value_usd": 1_000_000,
        "duration_days": 365,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_office_comes_from_the_piid():
    assert office_from_award_id("CONT_AWD_N0001902C3002_9700_-NONE-_-NONE-") == "N00019"
    assert office_from_award_id("HSTS0113FFIN011") == ""


def test_features_use_training_column_order_and_saved_categories():
    X = build_features(contracts(), CATEGORIES)
    assert list(X.columns) == FEATURES
    assert list(X["office"].cat.categories) == CATEGORIES["office"]
    assert X["office"].iloc[0] == "N00019"


def test_unseen_category_becomes_missing_not_an_error():
    X = build_features(contracts(naics_code="999999", psc_code="ZZZZ"), CATEGORIES)
    assert X["naics_code"].isna().all()
    assert X["psc_code"].isna().all()
    assert list(X["naics_code"].cat.categories) == CATEGORIES["naics_code"]


def test_model_labels_follow_the_cutoffs():
    assert recompete_model.interpret_recompete_model(0.5) == "HIGH"
    assert recompete_model.interpret_recompete_model(0.1) == "MEDIUM"
    assert recompete_model.interpret_recompete_model(0.01) == "LOW"


def test_missing_model_falls_back(monkeypatch):
    monkeypatch.setattr(recompete_model, "MODEL_PATH", recompete_model.MODEL_PATH.with_name("nope.json"))
    monkeypatch.setattr(recompete_model, "_cache", {})

    class Cur:
        def execute(self, *a): raise AssertionError("must not query when the model is unavailable")

    assert recompete_model.score_company(Cur(), "ACME") is None
