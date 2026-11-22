"""Phase 6: early-warning agent.

A weekly job. For each active loan it compares the vendor's last 4 weeks of UPI
inflow with the vendor's OWN median week over the 12 weeks before that, and flags:

* a sustained dip (most recent weeks well below the vendor's usual level), and
* a long dry spell (many days in a row with no UPI income).

Each flag carries a plain reason and a suggested action for a PERSON. The agent
never contacts the borrower: `auto_contact` is always False.

Run: python -m vendorscore.agents.early_warning   (writes reports/early_warning.json and .md)
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from vendorscore.config import ARTIFACT_DIR, REPORT_DIR, ensure_dirs, load_config
from vendorscore.data.synth import EMI_INTERVAL_DAYS, load_tables, observation_matrix
from vendorscore.logging_setup import get_logger

log = get_logger(__name__)

HUMAN_ONLY = ("Do not contact the borrower automatically. Any contact must be made by a person, "
              "following the lender's fair-practice code.")
ACTIONS = {
    "high": "Assign to a field officer for a check-in call or visit this week, before the next EMI. "
            "If the vendor reports hardship, discuss options under the lender's hardship policy.",
    "medium": "Add to this week's review list. A relationship manager may call to ask how the business is doing.",
}


@dataclass
class Alert:
    vendor_id: str
    as_of_day: int
    severity: str                  # "high" | "medium"
    flags: list[str]               # "sustained_dip", "long_dry_spell"
    reason: str
    suggested_action: str
    human_only_note: str
    auto_contact: bool
    recent_vs_baseline_pct: int
    baseline_weekly_median: int
    recent_weekly: list[int]
    dips_in_last_4_weeks: int
    longest_recent_dry_spell: int
    weekly_history: list[int]      # 16 weeks, oldest first (for charts)


def _weekly(window: np.ndarray, n_weeks: int) -> np.ndarray:
    """window: [n, n_weeks*7] daily inflow, oldest first -> [n, n_weeks] weekly totals."""
    return window.reshape(window.shape[0], n_weeks, 7).sum(axis=2)


def _longest_zero_run(x: np.ndarray) -> np.ndarray:
    run = np.zeros(x.shape[0], dtype=int)
    best = np.zeros(x.shape[0], dtype=int)
    for j in range(x.shape[1]):
        run = (run + 1) * (x[:, j] <= 0)
        best = np.maximum(best, run)
    return best


def assess(inflow: np.ndarray, vendor_ids: list[str] | np.ndarray, as_of_day: int, day0: int = 0) -> list[Alert]:
    """Assess many vendors at one as-of day.

    inflow: [n, days] daily inflow whose column 0 is `day0`. Uses data strictly before `as_of_day`.
    """
    cfg = load_config()["early_warning"]
    bw, rw = int(cfg["baseline_weeks"]), int(cfg["recent_weeks"])
    end = as_of_day - day0
    start = end - (bw + rw) * 7
    if start < 0:
        return []
    win = inflow[:, start:end]
    weeks = _weekly(win, bw + rw)
    base = np.median(weeks[:, :bw], axis=1)
    recent = weeks[:, bw:]
    safe = np.maximum(base, 1.0)
    ratio = recent / safe[:, None]
    dips = (ratio < cfg["dip_ratio"]).sum(axis=1)
    mean_ratio = recent.mean(axis=1) / safe
    dry = _longest_zero_run(win[:, -rw * 7 :])

    has_base = base > 0
    dip_flag = has_base & (dips >= cfg["min_dip_weeks"]) & (mean_ratio < cfg["mean_ratio_max"])
    dry_flag = dry >= cfg["dry_spell_days"]
    alerts: list[Alert] = []
    for i in np.where(dip_flag | dry_flag)[0]:
        flags = []
        parts = []
        if dip_flag[i]:
            flags.append("sustained_dip")
            parts.append(f"UPI income over the last {rw} weeks averaged {mean_ratio[i]:.0%} of this vendor's usual "
                         f"week (Rs {recent[i].mean():,.0f} vs a {bw}-week median of Rs {base[i]:,.0f}); "
                         f"{dips[i]} of {rw} weeks were below {cfg['dip_ratio']:.0%}.")
        if dry_flag[i]:
            flags.append("long_dry_spell")
            parts.append(f"No UPI income for {dry[i]} days in a row within the last {rw} weeks.")
        high = bool((dip_flag[i] and dry_flag[i]) or (has_base[i] and mean_ratio[i] < cfg["high_severity_ratio"]))
        sev = "high" if high else "medium"
        alerts.append(Alert(
            vendor_id=str(vendor_ids[i]), as_of_day=int(as_of_day), severity=sev, flags=flags,
            reason=" ".join(parts), suggested_action=ACTIONS[sev], human_only_note=HUMAN_ONLY, auto_contact=False,
            recent_vs_baseline_pct=int(round(100 * mean_ratio[i])) if has_base[i] else 0,
            baseline_weekly_median=int(round(base[i])), recent_weekly=[int(round(v)) for v in recent[i]],
            dips_in_last_4_weeks=int(dips[i]), longest_recent_dry_spell=int(dry[i]),
            weekly_history=[int(round(v)) for v in weeks[i]],
        ))
    alerts.sort(key=lambda a: (a.severity != "high", a.recent_vs_baseline_pct))
    return alerts


def run_weekly(tables: dict[str, pd.DataFrame], as_of_day: int, vendor_ids: list[str] | None = None) -> list[Alert]:
    """The weekly job: assess every loan that is active on `as_of_day`."""
    v = tables["vendors"]
    if vendor_ids is not None:
        v = v[v.vendor_id.isin(vendor_ids)]
    horizon_end = v.origination_day + EMI_INTERVAL_DAYS * np.minimum(12, v.tenure_months)
    missed = v.first_missed_day.fillna(10**9).astype(int)
    active = (v.origination_day < as_of_day) & (as_of_day <= horizon_end) & (as_of_day <= missed)
    ids = v.vendor_id[active].to_numpy()
    inflow = observation_matrix(tables["daily_upi"], ids, 0, as_of_day)
    alerts = assess(inflow, ids, as_of_day)
    log.info("weekly run day %d: %d active loans, %d alerts", as_of_day, len(ids), len(alerts))
    return alerts


# --------------------------------------------------------------------------- #
# Evaluation on synthetic data
# --------------------------------------------------------------------------- #
def evaluate_ews(tables: dict[str, pd.DataFrame] | None = None, vendor_ids: list[str] | None = None) -> dict[str, Any]:
    cfg = load_config()["early_warning"]
    tables = tables or load_tables()
    v = tables["vendors"]
    if vendor_ids is not None:
        v = v[v.vendor_id.isin(set(vendor_ids))]
    v = v.reset_index(drop=True)
    hidden = tables["hidden_traits"].set_index("vendor_id").loc[v.vendor_id]
    ids = v.vendor_id.to_numpy()
    total = int(tables["daily_upi"].day.max()) + 1
    inflow = observation_matrix(tables["daily_upi"], ids, 0, total)
    orig = int(v.origination_day.iloc[0])
    horizon_end = (orig + EMI_INTERVAL_DAYS * np.minimum(12, v.tenure_months)).to_numpy()
    missed = v.first_missed_day.fillna(10**9).astype(int).to_numpy()
    is_bad = v.default_12m.to_numpy() == 1
    idx_of = {vid: i for i, vid in enumerate(ids)}

    first_flag = np.full(len(v), -1)
    n_alerts = 0
    useful_alerts = 0
    by_sev = {"high": [0, 0], "medium": [0, 0]}
    horizon = int(cfg["outcome_horizon_days"])
    for as_of in range(orig + 7, int(horizon_end.max()) + 1, 7):
        active = (as_of <= horizon_end) & (as_of <= missed)
        if not active.any():
            continue
        alerts = assess(inflow[active], ids[active], as_of)
        for a in alerts:
            i = idx_of[a.vendor_id]
            n_alerts += 1
            hit = bool(is_bad[i] and missed[i] - as_of <= horizon)
            useful_alerts += hit
            by_sev[a.severity][0] += 1
            by_sev[a.severity][1] += hit
            if first_flag[i] < 0:
                first_flag[i] = as_of

    flagged = first_flag >= 0
    tp = flagged & is_bad
    lead = (missed - first_flag)[tp]
    visible = hidden.distress_visible_in_upi.to_numpy()
    temp_dip = hidden.temporary_dip_good_payer.to_numpy()

    def r(x: float) -> float:
        return round(float(x), 4)

    res = {
        "data": "SYNTHETIC - not evidence of real-world performance",
        "setup": {"vendors": int(len(v)), "defaulters": int(is_bad.sum()),
                  "weekly_runs": "every 7 days from origination until the first missed EMI or the end of the 12-month window",
                  "thresholds": cfg},
        "vendor_level": {
            "recall": r(tp.sum() / max(is_bad.sum(), 1)),
            "precision": r(tp.sum() / max(flagged.sum(), 1)),
            "flagged_vendors": int(flagged.sum()),
            "true_positives": int(tp.sum()),
            "good_payers_flagged_share": r((flagged & ~is_bad).sum() / max((~is_bad).sum(), 1)),
            "base_default_rate": r(is_bad.mean()),
        },
        "alert_level": {"alerts": n_alerts, "precision_missed_within_horizon": r(useful_alerts / max(n_alerts, 1)),
                        "horizon_days": horizon,
                        "by_severity": {k: {"alerts": a, "precision": r(h / max(a, 1))} for k, (a, h) in by_sev.items()}},
        "lead_time_days": {
            "median": float(np.median(lead)) if len(lead) else None,
            "p25": float(np.percentile(lead, 25)) if len(lead) else None,
            "p75": float(np.percentile(lead, 75)) if len(lead) else None,
            "share_at_least_14_days": r((lead >= 14).mean()) if len(lead) else None,
            "share_at_least_30_days": r((lead >= 30).mean()) if len(lead) else None,
        },
        "diagnostics_synthetic_only": {
            "recall_when_distress_visible_in_upi": r((tp & visible).sum() / max((is_bad & visible).sum(), 1)),
            "recall_when_distress_not_visible": r((tp & ~visible).sum() / max((is_bad & ~visible).sum(), 1)),
            "share_of_false_alarms_with_temporary_dip": r((flagged & ~is_bad & temp_dip).sum()
                                                         / max((flagged & ~is_bad).sum(), 1)),
        },
    }
    return res


def to_markdown(r: dict[str, Any]) -> str:
    vl, al, lt, dg = r["vendor_level"], r["alert_level"], r["lead_time_days"], r["diagnostics_synthetic_only"]
    return "\n".join([
        "# Early-warning agent report (SYNTHETIC DATA)", "",
        "> Synthetic data. These numbers show the method works; they are not real-world performance.", "",
        f"{r['setup']['vendors']} loans ({r['setup'].get('evaluated_on', 'all vendors')}), {r['setup']['defaulters']} defaults. "
        f"Weekly runs {r['setup']['weekly_runs']}. Thresholds were tuned on the training vendors only.", "",
        "## Vendor level", "",
        f"* Recall (defaulters flagged before their first missed EMI): **{vl['recall']:.1%}**",
        f"* Precision (flagged vendors who went on to miss a payment): **{vl['precision']:.1%}** "
        f"(base default rate {vl['base_default_rate']:.1%}, so a random flag would be right {vl['base_default_rate']:.1%} of the time)",
        f"* Good payers flagged at least once: {vl['good_payers_flagged_share']:.1%}", "",
        "## Lead time before the first missed EMI (true positives)", "",
        f"* Median **{lt['median']} days** (IQR {lt['p25']}-{lt['p75']})",
        f"* At least 14 days ahead: {lt['share_at_least_14_days']:.0%}; at least 30 days ahead: {lt['share_at_least_30_days']:.0%}", "",
        "## Alert level", "",
        f"* {al['alerts']} weekly alerts; {al['precision_missed_within_horizon']:.1%} were followed by a missed EMI within "
        f"{al['horizon_days']} days",
        *[f"* {k} severity: {d['alerts']} alerts, {d['precision']:.1%} followed by a missed EMI within {al['horizon_days']} days"
          for k, d in al["by_severity"].items()], "",
        "## Diagnostics (uses hidden synthetic traits)", "",
        f"* Recall when distress shows in UPI: {dg['recall_when_distress_visible_in_upi']:.1%}; "
        f"when it does not: {dg['recall_when_distress_not_visible']:.1%}",
        f"* Share of false alarms that were good payers with a temporary dip: {dg['share_of_false_alarms_with_temporary_dip']:.1%}",
        "",
    ])


def run() -> dict[str, Any]:
    ensure_dirs()
    split_path = ARTIFACT_DIR / "split.json"
    test_ids = json.loads(split_path.read_text())["test_vendor_ids"] if split_path.exists() else None
    res = evaluate_ews(vendor_ids=test_ids)
    res["setup"]["evaluated_on"] = "held-out test vendors" if test_ids else "all vendors"
    (REPORT_DIR / "early_warning.json").write_text(json.dumps(res, indent=2))
    (REPORT_DIR / "early_warning.md").write_text(to_markdown(res))
    log.info("EWS recall %.3f precision %.3f median lead %s days", res["vendor_level"]["recall"],
             res["vendor_level"]["precision"], res["lead_time_days"]["median"])
    return res


def alerts_as_dicts(alerts: list[Alert]) -> list[dict[str, Any]]:
    return [asdict(a) for a in alerts]


if __name__ == "__main__":
    run()
