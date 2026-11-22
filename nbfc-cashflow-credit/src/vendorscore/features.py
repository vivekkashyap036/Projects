"""Phase 2: explainable cash-flow features from daily UPI inflow.

Every feature is something a credit officer can check by eye on a chart of the
vendor's daily receipts. Expected direction is on the probability of DEFAULT.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vendorscore.config import load_config


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    label: str
    expected_sign: int   # +1: higher value -> higher default risk; -1: lower risk


FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("log_income_to_emi", "UPI income relative to EMI (log)", -1),
    FeatureSpec("weekly_cv", "Week-to-week income variability (open weeks)", +1),
    FeatureSpec("longest_dry_spell", "Longest run of zero-income days", +1),
    FeatureSpec("active_day_share", "Share of days the stall was active (not in a 2+ day closure)", -1),
    FeatureSpec("recent_trend", "Last 30 days vs the 60 days before (log ratio)", -1),
)
FEATURE_NAMES: list[str] = [f.name for f in FEATURES]
EXPECTED_SIGN: dict[str, int] = {f.name: f.expected_sign for f in FEATURES}

DRY_SPELL_CAP = 45  # days; caps leverage of extreme closures


def _longest_zero_run(x: np.ndarray) -> np.ndarray:
    """Longest run of zeros per row of a 2-D array."""
    zero = (x <= 0).astype(np.int32)
    run = np.zeros(x.shape[0], dtype=np.int32)
    best = np.zeros(x.shape[0], dtype=np.int32)
    for j in range(x.shape[1]):
        run = (run + 1) * zero[:, j]
        best = np.maximum(best, run)
    return best


def feature_matrix(inflow: np.ndarray, emi: np.ndarray) -> dict[str, np.ndarray]:
    """Compute features for many vendors.

    inflow: [n_vendors, n_days] daily UPI inflow (most recent day last), gaps already zero-filled.
    emi:    [n_vendors] monthly instalment in rupees.
    Returns raw features plus a few display helpers (income_to_emi, monthly_upi_income).
    """
    cfg = load_config()["features"]
    inflow = np.asarray(inflow, dtype=float)
    if inflow.ndim != 2:
        raise ValueError("inflow must be 2-D [vendors, days]")
    inflow = inflow[:, -int(cfg["max_days"]):]
    n_days = inflow.shape[1]
    emi = np.asarray(emi, dtype=float)

    monthly = inflow.mean(axis=1) * 30.0
    income_to_emi = monthly / np.maximum(emi, 1.0)

    # Weekly variability is measured on "open" weeks (6+ days with UPI income) so that
    # closures are counted once, by the dry-spell feature, and not again here.
    n_weeks = n_days // 7
    wk = inflow[:, n_days - n_weeks * 7 :].reshape(inflow.shape[0], n_weeks, 7)
    weeks = wk.sum(axis=2)
    open_wk = (wk > 0).sum(axis=2) >= 6
    cnt = open_wk.sum(axis=1)
    wsum = np.where(open_wk, weeks, 0.0).sum(axis=1)
    wmean = wsum / np.maximum(cnt, 1)
    wvar = np.where(open_wk, (weeks - wmean[:, None]) ** 2, 0.0).sum(axis=1) / np.maximum(cnt, 1)
    weekly_cv = np.where((cnt >= 4) & (wmean > 0), np.sqrt(wvar) / np.maximum(wmean, 1e-9), 1.0)
    weekly_cv = np.minimum(weekly_cv, 3.0)

    longest = np.minimum(_longest_zero_run(inflow), DRY_SPELL_CAP).astype(float)
    # An "active" day is any day that is not part of a closure (2+ zero-income days in a row).
    # A single zero day on a small stall usually means no UPI customer that day, not a closure.
    zero = inflow <= 0
    prev = np.zeros_like(zero)
    prev[:, 1:] = zero[:, :-1]
    nxt = np.zeros_like(zero)
    nxt[:, :-1] = zero[:, 1:]
    active_share = 1.0 - (zero & (prev | nxt)).mean(axis=1)

    r, p = int(cfg["recent_window_days"]), int(cfg["prior_window_days"])
    recent = inflow[:, -r:].mean(axis=1)
    prior = inflow[:, -(r + p) : -r].mean(axis=1)
    recent_trend = np.clip(np.log((recent + 1.0) / (prior + 1.0)), -2.0, 2.0)

    return {
        "log_income_to_emi": np.log(np.clip(income_to_emi, 0.05, 100.0)),
        "weekly_cv": weekly_cv,
        "longest_dry_spell": longest,
        "active_day_share": active_share,
        "recent_trend": recent_trend,
        # display helpers, not model inputs
        "income_to_emi": income_to_emi,
        "monthly_upi_income": monthly,
        "n_days": np.full(inflow.shape[0], n_days, dtype=float),
    }


def records_to_series(records: list[dict], max_days: int | None = None) -> np.ndarray:
    """Turn API daily records [{day, n_txn, inflow}] into a zero-filled daily series."""
    if not records:
        return np.zeros(0)
    days = np.array([int(r["day"]) for r in records])
    vals = np.array([float(r["inflow"]) for r in records])
    start, end = days.min(), days.max()
    series = np.zeros(end - start + 1)
    np.add.at(series, days - start, vals)
    if max_days:
        series = series[-max_days:]
    return series
