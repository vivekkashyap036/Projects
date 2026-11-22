"""Phase 1: synthetic vendor, UPI and repayment data.

Everything here is SYNTHETIC. The generator is built so that the model sees only
part of the truth:

* Each vendor has hidden traits (true income, cash share, market-day boost,
  seasonality, trend, volatility, dry-spell propensity, profit margin, resilience).
* The model only sees daily UPI receipts, which miss the cash share of sales.
* Repayment outcomes are drawn from the hidden TRUE income and traits plus noise,
  so a cash-heavy vendor can repay well even if their UPI looks thin.
* After the loan starts, defaulters go through a "distress" period before their
  first missed EMI (visible in UPI for most, not all), and some good payers have
  temporary dips. This is what the early-warning agent is evaluated on.

Run: python -m vendorscore.data.synth
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from vendorscore.config import DATA_DIR, ensure_dirs, load_config
from vendorscore.logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class VendorTypeSpec:
    share: float           # share of the population
    median_income: float   # median TRUE daily sales, rupees
    avg_ticket: float      # average UPI payment size, rupees
    cash_mean: float       # mean share of sales taken in cash


VENDOR_TYPES: dict[str, VendorTypeSpec] = {
    "vegetable_seller": VendorTypeSpec(0.25, 1800, 80, 0.55),
    "fruit_cart": VendorTypeSpec(0.15, 1500, 90, 0.55),
    "tea_stall": VendorTypeSpec(0.18, 1100, 20, 0.60),
    "street_food": VendorTypeSpec(0.17, 2200, 60, 0.50),
    "kirana_shop": VendorTypeSpec(0.15, 3500, 150, 0.40),
    "flower_seller": VendorTypeSpec(0.10, 900, 50, 0.60),
}

TENURES = np.array([6, 9, 12, 18, 24])
TENURE_P = np.array([0.15, 0.20, 0.35, 0.20, 0.10])
EMI_INTERVAL_DAYS = 30


def emi_amount(principal: np.ndarray, annual_rate: np.ndarray, tenure_months: np.ndarray) -> np.ndarray:
    """Standard reducing-balance EMI."""
    r = annual_rate / 12.0
    f = (1 + r) ** tenure_months
    return principal * r * f / (f - 1)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _calibrate_intercept(logit_wo_b0: np.ndarray, target: float) -> float:
    lo, hi = -20.0, 20.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _sigmoid(logit_wo_b0 + mid).mean() > target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def generate(n_vendors: int | None = None, seed: int | None = None) -> dict[str, pd.DataFrame]:
    cfg = load_config()
    n = int(n_vendors or cfg["data"]["n_vendors"])
    seed = int(cfg["seed"] if seed is None else seed)
    obs_days = int(cfg["data"]["observation_days"])
    perf_days = int(cfg["data"]["performance_days"])
    total_days = obs_days + perf_days
    rng = np.random.default_rng(seed)

    # ---- vendor types and hidden traits ------------------------------------
    names = list(VENDOR_TYPES)
    probs = np.array([VENDOR_TYPES[k].share for k in names])
    vtype_idx = rng.choice(len(names), size=n, p=probs / probs.sum())
    spec_median = np.array([VENDOR_TYPES[names[i]].median_income for i in vtype_idx])
    spec_ticket = np.array([VENDOR_TYPES[names[i]].avg_ticket for i in vtype_idx])
    spec_cash = np.array([VENDOR_TYPES[names[i]].cash_mean for i in vtype_idx])

    true_daily_income = spec_median * np.exp(rng.normal(0, 0.45, n))
    conc = 8.0
    cash_share = np.clip(rng.beta(spec_cash * conc, (1 - spec_cash) * conc), 0.05, 0.95)
    market_day = rng.integers(0, 7, n)
    market_boost = rng.uniform(1.0, 1.8, n)
    season_amp = rng.uniform(0.0, 0.25, n)
    season_phase = rng.uniform(0, 2 * np.pi, n)
    trend_monthly = np.clip(rng.normal(0.0, 0.025, n), -0.06, 0.06)
    volatility = rng.uniform(0.15, 0.60, n)
    dry_rate = rng.gamma(1.5, 1.0, n)            # expected dry-spell events per 180 days
    profit_margin = rng.uniform(0.20, 0.40, n)   # share of sales left after stock costs
    resilience = rng.normal(0, 1, n)             # savings / family support (never observed)

    # ---- true daily sales ---------------------------------------------------
    t = np.arange(total_days)
    weekday = t % 7
    weekly = np.where(weekday[None, :] == market_day[:, None], market_boost[:, None], 1.0)
    # normalise so the average weekly multiplier is 1
    weekly = weekly / ((6 + market_boost) / 7)[:, None]
    season = 1 + season_amp[:, None] * np.sin(2 * np.pi * t[None, :] / 365 + season_phase[:, None])
    trend = np.exp((trend_monthly / 30)[:, None] * (t[None, :] - obs_days))
    noise = np.exp(rng.normal(-0.5 * volatility[:, None] ** 2, volatility[:, None], (n, total_days)))
    active = np.ones((n, total_days), dtype=bool)

    def add_spells(i: int, start_day: int, end_day: int, rate_per_180: float) -> None:
        span = end_day - start_day
        k = rng.poisson(rate_per_180 * span / 180)
        for _ in range(k):
            kind = rng.choice(3, p=[0.35, 0.45, 0.20])   # illness, rain, closure
            length = [rng.integers(3, 13), rng.integers(1, 5), rng.integers(5, 26)][kind]
            s = rng.integers(start_day, end_day)
            active[i, s : s + length] = False

    for i in range(n):
        add_spells(i, 0, total_days, dry_rate[i])

    true_sales = true_daily_income[:, None] * weekly * season * trend * noise

    # ---- loan terms (sized by a field officer who sees roughly true income) --
    true_monthly = true_daily_income * 30
    officer_view = true_monthly * np.exp(rng.normal(0, 0.25, n))
    amount = np.clip(np.round(officer_view * rng.uniform(0.4, 1.6, n) / 5000) * 5000, 10000, 150000)
    tenure = rng.choice(TENURES, size=n, p=TENURE_P)
    annual_rate = np.round(rng.uniform(0.22, 0.30, n) * 200) / 200
    emi = np.round(emi_amount(amount, annual_rate, tenure), 0)

    # ---- repayment outcome from HIDDEN truth ---------------------------------
    active_share_true = active[:, :obs_days].mean(axis=1)
    capacity = true_monthly * profit_margin * active_share_true
    burden = emi / capacity
    logit = (
        1.7 * np.log(burden)
        + 3.0 * (volatility - 0.375)
        + 0.35 * (dry_rate - 1.5)
        - 12.0 * trend_monthly
        - 0.55 * resilience
        + rng.normal(0, 0.6, n)
    )
    b0 = _calibrate_intercept(logit, float(cfg["data"]["target_default_rate"]))
    pd_true = _sigmoid(logit + b0)
    default = rng.random(n) < pd_true

    # ---- performance window: distress before the first missed EMI -----------
    horizon_months = np.minimum(12, tenure)
    first_missed_day = np.full(n, -1, dtype=int)
    distress_onset = np.full(n, -1, dtype=int)
    distress_visible = np.zeros(n, dtype=bool)
    temp_dip = np.zeros(n, dtype=bool)
    for i in np.where(default)[0]:
        h = int(horizon_months[i])
        w = np.linspace(1.4, 0.6, h)          # misses skew earlier in the loan
        k = int(rng.choice(np.arange(1, h + 1), p=w / w.sum()))
        due = obs_days + k * EMI_INTERVAL_DAYS
        lag = int(rng.integers(14, 76))
        onset = max(obs_days + 1, due - lag)
        first_missed_day[i] = due
        distress_onset[i] = onset
        if rng.random() < 0.75:                # 25% of defaults give no UPI warning
            distress_visible[i] = True
            if rng.random() < 0.6:
                true_sales[i, onset:] *= rng.uniform(0.2, 0.55)
            else:
                closure = int(rng.integers(10, 31))
                active[i, onset : onset + closure] = False
                true_sales[i, onset + closure :] *= rng.uniform(0.4, 0.7)
    for i in np.where(~default)[0]:
        if rng.random() < 0.15:                # good payers with a temporary dip
            temp_dip[i] = True
            s = int(rng.integers(obs_days + 1, total_days - 20))
            length = int(rng.integers(14, 43))
            true_sales[i, s : s + length] *= rng.uniform(0.4, 0.7)

    true_sales = np.where(active, true_sales, 0.0)

    # ---- observed UPI --------------------------------------------------------
    upi_amount = true_sales * (1 - cash_share)[:, None] * np.exp(rng.normal(-0.01, 0.15, true_sales.shape))
    n_txn = rng.poisson(upi_amount / spec_ticket[:, None])
    ticket_noise = np.exp(rng.normal(0, 0.3 / np.sqrt(np.maximum(n_txn, 1))))
    inflow = np.round(n_txn * spec_ticket[:, None] * ticket_noise, 0)

    vendor_ids = np.array([f"V{i + 1:06d}" for i in range(n)])
    vendors = pd.DataFrame(
        {
            "vendor_id": vendor_ids,
            "vendor_type": [names[i] for i in vtype_idx],
            "loan_amount": amount.astype(int),
            "tenure_months": tenure.astype(int),
            "annual_rate": annual_rate,
            "emi": emi.astype(int),
            "origination_day": obs_days,
            "default_12m": default.astype(int),
            "first_missed_day": pd.array(np.where(first_missed_day >= 0, first_missed_day, None), dtype="Int64"),
        }
    )
    daily = pd.DataFrame(
        {
            "vendor_id": np.repeat(vendor_ids, total_days),
            "day": np.tile(t, n).astype(np.int16),
            "n_txn": n_txn.ravel().astype(np.int32),
            "inflow": inflow.ravel().astype(np.float32),
        }
    )
    hidden = pd.DataFrame(
        {
            "vendor_id": vendor_ids,
            "true_daily_income": true_daily_income.round(1),
            "cash_share": cash_share.round(3),
            "market_day": market_day,
            "market_boost": market_boost.round(3),
            "season_amp": season_amp.round(3),
            "trend_monthly": trend_monthly.round(4),
            "volatility": volatility.round(3),
            "dry_spell_rate_per_180d": dry_rate.round(3),
            "profit_margin": profit_margin.round(3),
            "resilience": resilience.round(3),
            "true_pd": pd_true.round(4),
            "distress_onset_day": pd.array(np.where(distress_onset >= 0, distress_onset, None), dtype="Int64"),
            "distress_visible_in_upi": distress_visible,
            "temporary_dip_good_payer": temp_dip,
        }
    )
    log.info(
        "generated %d vendors x %d days; default rate %.2f%%", n, total_days, 100 * vendors.default_12m.mean()
    )
    return {"vendors": vendors, "daily_upi": daily, "hidden_traits": hidden}


def save(tables: dict[str, pd.DataFrame]) -> None:
    ensure_dirs()
    for name, df in tables.items():
        path = DATA_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        log.info("wrote %s (%d rows)", path, len(df))


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_parquet(DATA_DIR / f"{name}.parquet")
        for name in ("vendors", "daily_upi", "hidden_traits")
    }


def observation_matrix(daily: pd.DataFrame, vendor_ids: list[str] | np.ndarray, start: int, end: int) -> np.ndarray:
    """Inflow matrix [vendor, day] for days start..end-1, rows in vendor_ids order."""
    sub = daily[(daily.day >= start) & (daily.day < end)]
    piv = sub.pivot(index="vendor_id", columns="day", values="inflow").reindex(vendor_ids)
    return piv.fillna(0.0).to_numpy(dtype=float)


if __name__ == "__main__":
    save(generate())
