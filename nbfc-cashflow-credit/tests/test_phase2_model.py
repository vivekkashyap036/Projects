"""Phase 2: coefficient signs, monotonicity, score scaling, bands, reason codes, determinism."""
from __future__ import annotations

import math

import numpy as np
import pytest

from vendorscore import model
from vendorscore.config import load_config
from vendorscore.features import EXPECTED_SIGN, FEATURE_NAMES, feature_matrix


def test_coefficient_signs_match_expected_direction(trained):
    scorer, _, _ = trained
    for f, c in zip(scorer.feature_names, scorer.coef):
        assert c != 0, f"{f} pinned at 0 by the sign constraint: feature carries no usable signal"
        assert np.sign(c) == EXPECTED_SIGN[f], f"{f}: coef {c:+.4f} has the wrong sign"


def _series(level: float, days: int = 180, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return level * np.exp(rng.normal(0, 0.3, days))


def test_monotonic_in_income_vs_emi(trained):
    """Higher UPI income relative to the same EMI must never raise risk."""
    scorer, _, _ = trained
    base = _series(1.0)
    pds = [scorer.score_one(base * lvl, emi=5000)["probability_of_default"] for lvl in (200, 400, 800, 1600, 3200)]
    assert all(a >= b for a, b in zip(pds, pds[1:])), pds
    scores = [scorer.score_one(base * 800, emi=e)["score"] for e in (2000, 4000, 8000, 16000)]
    assert all(a >= b for a, b in zip(scores, scores[1:])), scores


def test_monotonic_in_dry_spell(trained):
    scorer, _, _ = trained
    s = _series(1000)
    prev = None
    for gap in (0, 5, 10, 20):
        x = s.copy()
        x[60 : 60 + gap] = 0
        sc = scorer.score_one(x, emi=6000)["score"]
        if prev is not None:
            assert sc <= prev
        prev = sc


def test_pdo_doubles_odds():
    cfg = load_config()["scorecard"]
    p1 = 0.10
    odds1 = (1 - p1) / p1
    odds2 = 2 * odds1
    p2 = 1 / (1 + odds2)
    assert abs(model.pd_to_score(p2) - model.pd_to_score(p1) - cfg["pdo"]) <= 1
    anchor_pd = 1 / (1 + cfg["anchor_odds"])
    assert abs(model.pd_to_score(anchor_pd) - cfg["anchor_score"]) <= 1


def test_score_range():
    assert model.pd_to_score(0.999999) == 300
    assert model.pd_to_score(1e-9) == 900


@pytest.mark.parametrize("delta,expected", [(0, "approve"), (-1, "review"), (None, "review")])
def test_band_thresholds(delta, expected):
    b = load_config()["bands"]
    score = b["approve_min"] + delta if delta is not None else b["decline_below"]
    assert model.score_to_band(score) == expected


def test_band_decline_edge():
    b = load_config()["bands"]
    assert model.score_to_band(b["decline_below"] - 1) == "decline"
    assert b["decline_below"] < b["approve_min"]


def test_reason_codes_are_plain_language(trained):
    scorer, _, te = trained
    from vendorscore.data.synth import observation_matrix  # noqa: F401
    s = _series(300)
    s[100:115] = 0
    out = scorer.score_one(s, emi=8000)
    assert out["band"] in {"approve", "review", "decline"}
    assert out["human_review_required"] == (out["band"] != "approve")
    assert out["reasons"], "a risky profile must come with reasons"
    for r in out["reasons"]:
        assert r["direction"] == "increases_risk"
        assert r["code"].startswith("R")
        assert len(r["text_en"]) > 20 and "log" not in r["text_en"].lower()
        assert r["text_hi"]


def test_training_is_deterministic(full_tables):
    df = model.build_dataset(full_tables)
    tr, _ = model.split(df)
    a = model.fit_logreg(tr)
    b = model.fit_logreg(tr)
    assert a.coef == b.coef and a.intercept == b.intercept


def test_scoring_is_deterministic(trained):
    scorer, _, _ = trained
    s = _series(900)
    assert scorer.score_one(s, 4000) == scorer.score_one(s, 4000)


def test_feature_matrix_basic():
    x = np.full((1, 120), 100.0)
    x[0, 10:17] = 0
    f = feature_matrix(x, np.array([1000.0]))
    assert f["longest_dry_spell"][0] == 7
    assert math.isclose(f["income_to_emi"][0], 100 * 113 / 120 * 30 / 1000, rel_tol=1e-9)
    assert f["recent_trend"][0] == 0.0
    assert set(FEATURE_NAMES) <= set(f)
