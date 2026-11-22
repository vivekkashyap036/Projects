"""Phase 1: synthetic data shape, plausibility and determinism."""
from __future__ import annotations

import pandas as pd

from vendorscore.data import synth

VENDOR_COLS = {"vendor_id", "vendor_type", "loan_amount", "tenure_months", "annual_rate", "emi",
               "origination_day", "default_12m", "first_missed_day"}
DAILY_COLS = {"vendor_id", "day", "n_txn", "inflow"}


def test_schema(small_tables):
    assert set(small_tables["vendors"].columns) == VENDOR_COLS
    assert set(small_tables["daily_upi"].columns) == DAILY_COLS


def test_hidden_traits_not_in_model_tables(small_tables):
    hidden = set(small_tables["hidden_traits"].columns) - {"vendor_id"}
    assert not hidden & set(small_tables["vendors"].columns)
    assert not hidden & set(small_tables["daily_upi"].columns)


def test_daily_records_consistent(small_tables):
    d = small_tables["daily_upi"]
    assert (d.inflow >= 0).all() and (d.n_txn >= 0).all()
    assert (d.loc[d.n_txn == 0, "inflow"] == 0).all()
    per_vendor = d.groupby("vendor_id").size()
    assert per_vendor.nunique() == 1 and per_vendor.iloc[0] == 545


def test_default_rate_near_target(small_tables):
    rate = small_tables["vendors"].default_12m.mean()
    assert 0.07 <= rate <= 0.12


def test_defaulters_have_missed_day_after_origination(small_tables):
    v = small_tables["vendors"]
    bad = v[v.default_12m == 1]
    assert bad.first_missed_day.notna().all()
    assert (bad.first_missed_day > bad.origination_day).all()
    assert v[v.default_12m == 0].first_missed_day.isna().all()


def test_emi_formula():
    import numpy as np
    emi = synth.emi_amount(np.array([12000.0]), np.array([0.24]), np.array([12]))[0]
    assert abs(emi - 1134.6) < 1.0


def test_determinism():
    a = synth.generate(n_vendors=200, seed=11)
    b = synth.generate(n_vendors=200, seed=11)
    for k in a:
        pd.testing.assert_frame_equal(a[k], b[k])
