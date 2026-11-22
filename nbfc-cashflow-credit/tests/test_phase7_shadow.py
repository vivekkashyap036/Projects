"""Phase 7: shadow mode is read-only, uses only known outcomes, always reports the baseline."""
from __future__ import annotations

import pandas as pd
import pytest

from vendorscore.agents import shadow


@pytest.fixture(scope="module")
def inputs(small_tables):
    loans, daily = shadow.make_sample_inputs(small_tables, seed=3)
    return loans.head(600).reset_index(drop=True), daily


def test_report_does_not_modify_inputs(inputs, trained):
    loans, daily = inputs
    l0, d0 = loans.copy(), daily.copy()
    r = shadow.shadow_report(loans, daily, trained[0])
    pd.testing.assert_frame_equal(loans, l0)
    pd.testing.assert_frame_equal(daily, d0)
    assert "No real lending decision was changed" in r["notice"]


def test_baseline_always_reported(inputs, trained):
    r = shadow.shadow_report(*inputs, trained[0])
    assert "baseline_rule" in r and "if_applied_to_lender_approvals" in r["baseline_rule"]
    assert r["inputs"]["approved_with_known_outcome"] == r["inputs"]["lender_approved"]


def test_declined_outcomes_are_ignored(inputs, trained):
    loans, daily = inputs
    a = shadow.shadow_report(loans, daily, trained[0])
    leaked = loans.copy()
    leaked.loc[leaked.lender_decision == "decline", "default_12m"] = 1  # should never be read
    b = shadow.shadow_report(leaked, daily, trained[0])
    assert a["model"]["default_rate_by_band_among_lender_approvals"] == b["model"]["default_rate_by_band_among_lender_approvals"]


def test_short_history_not_scored(inputs, trained):
    loans, daily = inputs
    vid = loans.vendor_id.iloc[0]
    daily = daily[(daily.vendor_id != vid) | (daily.day >= 150)]
    r = shadow.shadow_report(loans, daily, trained[0])
    assert r["inputs"]["not_scored_insufficient_history"] == 1


def test_bad_input_rejected(inputs, trained):
    loans, daily = inputs
    with pytest.raises(shadow.ShadowInputError):
        shadow.shadow_report(loans.drop(columns=["lender_decision"]), daily, trained[0])
    bad = loans.copy()
    bad.loc[0, "lender_decision"] = "maybe"
    with pytest.raises(shadow.ShadowInputError):
        shadow.shadow_report(bad, daily, trained[0])
