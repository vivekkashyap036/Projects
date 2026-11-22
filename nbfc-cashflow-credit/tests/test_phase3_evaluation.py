"""Phase 3: metric helpers and the evaluation report contract."""
from __future__ import annotations

import numpy as np
import pytest

from vendorscore import evaluate as ev


def test_ks_and_curves_on_toy_data():
    y = np.array([0, 0, 0, 0, 1, 1])
    perfect = np.array([0.1, 0.2, 0.3, 0.4, 0.8, 0.9])
    assert ev.ks_stat(y, perfect) == 1.0
    assert ev.default_at_approval_rate(y, perfect, 4 / 6) == 0.0
    assert ev.approval_at_default_rate(y, perfect, 0.0) == pytest.approx(4 / 6)
    curve = ev.approval_curve(y, perfect, steps=2)
    assert curve[-1]["default_rate_approved"] == pytest.approx(2 / 6, abs=1e-4)


def test_bootstrap_is_seeded():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    a, b = rng.random(300) + y * 0.3, rng.random(300)
    assert ev.bootstrap_auc_gain(y, a, b, 200, 1) == ev.bootstrap_auc_gain(y, a, b, 200, 1)


@pytest.fixture(scope="module")
def report(full_tables, trained):
    scorer, _, _ = trained
    return ev.evaluate(full_tables, scorer)


def test_report_always_contains_baseline_comparison(report):
    vs = report["vs_baseline"]
    for k in ("same_approval_rate", "same_default_rate", "auc_gain_vs_rule_binary", "auc_gain_vs_ratio_ranking"):
        assert k in vs
    g = vs["auc_gain_vs_rule_binary"]
    assert g["ci95_low"] <= g["gain"] <= g["ci95_high"]
    assert "SYNTHETIC" in report["data"]


def test_report_has_required_metrics(report):
    for k in ("auc", "ks", "brier"):
        assert k in report["logistic_regression"] and k in report["gradient_boosting_comparison"]
    assert len(report["calibration_by_decile"]) == 10
    assert report["approval_vs_default_curve"]["model"][-1]["approval_rate"] == 1.0
    assert {b["band"] for b in report["bands"]} == {"approve", "review", "decline"}


def test_bands_rank_risk(report):
    dr = {b["band"]: b["default_rate"] for b in report["bands"]}
    assert dr["approve"] < dr["review"] < dr["decline"]


def test_segments_flag_small_samples(report):
    for rows in report["segments"].values():
        for s in rows:
            assert s["weak"] == bool(s["flags"])
