"""Phase 6: early-warning rules, no look-ahead, human-only actions, evaluation contract."""
from __future__ import annotations

import numpy as np

from vendorscore.agents import early_warning as ew


def _base(days=140, level=1000.0, seed=0):
    rng = np.random.default_rng(seed)
    return level * np.exp(rng.normal(0, 0.15, days))


def test_stable_vendor_not_flagged():
    x = _base()[None, :]
    assert ew.assess(x, ["A"], as_of_day=140) == []


def test_sustained_dip_flagged():
    x = _base()
    x[-28:] *= 0.3
    alerts = ew.assess(x[None, :], ["A"], as_of_day=140)
    assert len(alerts) == 1
    a = alerts[0]
    assert "sustained_dip" in a.flags and a.severity == "high"
    assert a.recent_vs_baseline_pct < 40
    assert a.auto_contact is False
    assert "automatically" in a.human_only_note and a.suggested_action


def test_long_dry_spell_flagged():
    x = _base()
    x[-25:-2] = 0
    a = ew.assess(x[None, :], ["A"], as_of_day=140)[0]
    assert "long_dry_spell" in a.flags and a.longest_recent_dry_spell >= 21


def test_short_history_gives_no_alert():
    x = np.zeros((1, 100))
    assert ew.assess(x, ["A"], as_of_day=100) == []


def test_no_look_ahead():
    x = _base(160)
    x[112:140] *= 0.3
    y = x.copy()
    y[140:] = 99999  # data after as_of must not matter
    a = ew.assess(x[None, :], ["A"], as_of_day=140)
    b = ew.assess(y[None, :], ["A"], as_of_day=140)
    assert ew.alerts_as_dicts(a) == ew.alerts_as_dicts(b)


def test_evaluation_contract(small_tables):
    r = ew.evaluate_ews(small_tables)
    vl = r["vendor_level"]
    assert 0 <= vl["recall"] <= 1 and 0 <= vl["precision"] <= 1
    assert r["lead_time_days"]["median"] is None or r["lead_time_days"]["median"] > 0
    assert "SYNTHETIC" in r["data"]


def test_weekly_job_never_contacts(small_tables):
    alerts = ew.run_weekly(small_tables, as_of_day=300)
    assert alerts, "expected some alerts on synthetic data"
    assert all(a.auto_contact is False for a in alerts)
    assert all(a.as_of_day == 300 for a in alerts)
