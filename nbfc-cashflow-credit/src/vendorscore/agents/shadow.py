"""Phase 7: shadow-mode report.

Input: a CSV of past loans with the lender's actual decision and outcome, plus the
daily UPI records for those vendors. Output: how the model and the baseline rule
would have decided, compared with what the lender did. **No real decision is changed**:
the report only reads its inputs.

Important caveat built into the report: outcomes are only known for loans the lender
approved. For loans the lender declined we cannot say whether the model was right
(the "reject inference" problem). Those cases are counted, not scored.

Run: python -m vendorscore.agents.shadow   (builds a sample from synthetic test vendors and reports on it)
"""
from __future__ import annotations

import io
import json
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from vendorscore.config import ARTIFACT_DIR, DATA_DIR, REPORT_DIR, ensure_dirs, load_config
from vendorscore.data.synth import load_tables
from vendorscore.features import FEATURE_NAMES, feature_matrix, records_to_series
from vendorscore.logging_setup import get_logger
from vendorscore.model import CashFlowScorer, pd_to_score, score_to_band

log = get_logger(__name__)
REQUIRED_LOAN_COLS = {"vendor_id", "emi", "lender_decision"}
REQUIRED_DAILY_COLS = {"vendor_id", "day", "n_txn", "inflow"}


class ShadowInputError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# Sample input (synthetic)
# --------------------------------------------------------------------------- #
def make_sample_inputs(tables: dict[str, pd.DataFrame] | None = None, seed: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A synthetic 'past loans' file: test vendors, a simulated lender policy, outcomes only for approvals."""
    cfg = load_config()
    tables = tables or load_tables()
    rng = np.random.default_rng(cfg["seed"] + 1 if seed is None else seed)
    split_path = ARTIFACT_DIR / "split.json"
    v = tables["vendors"]
    if split_path.exists():
        v = v[v.vendor_id.isin(set(json.loads(split_path.read_text())["test_vendor_ids"]))]
    v = v.reset_index(drop=True)
    h = tables["hidden_traits"].set_index("vendor_id").loc[v.vendor_id]
    # Simulated lender: a field officer's noisy view of true income vs EMI, plus a dislike of very new/cash-heavy files.
    officer = np.log(h.true_daily_income.to_numpy() * 30 * 0.3 / v.emi.to_numpy()) + rng.normal(0, 0.6, len(v))
    approve = officer >= np.quantile(officer, 0.35)
    loans = pd.DataFrame({
        "vendor_id": v.vendor_id, "vendor_type": v.vendor_type, "loan_amount": v.loan_amount,
        "tenure_months": v.tenure_months, "emi": v.emi,
        "lender_decision": np.where(approve, "approve", "decline"),
        "default_12m": pd.array(np.where(approve, v.default_12m, None), dtype="Int64"),
    })
    d = tables["daily_upi"]
    obs = int(tables["vendors"].origination_day.iloc[0])
    daily = d[(d.vendor_id.isin(set(v.vendor_id))) & (d.day < obs)]
    return loans, daily.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def _validate(loans: pd.DataFrame, daily: pd.DataFrame) -> None:
    miss = REQUIRED_LOAN_COLS - set(loans.columns)
    if miss:
        raise ShadowInputError(f"loans file is missing columns: {sorted(miss)}")
    miss = REQUIRED_DAILY_COLS - set(daily.columns)
    if miss:
        raise ShadowInputError(f"daily file is missing columns: {sorted(miss)}")
    bad = set(loans.lender_decision.astype(str).str.lower()) - {"approve", "decline"}
    if bad:
        raise ShadowInputError(f"lender_decision must be approve/decline; found {sorted(bad)}")


def score_batch(scorer: CashFlowScorer, loans: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    cfg = load_config()["features"]
    groups = {k: g for k, g in daily.groupby("vendor_id")}
    rows = []
    for vid, emi in zip(loans.vendor_id, loans.emi):
        g = groups.get(vid)
        series = records_to_series(g[["day", "n_txn", "inflow"]].to_dict("records"), cfg["max_days"]) if g is not None else np.zeros(0)
        if len(series) < cfg["min_days"]:
            rows.append({"vendor_id": vid, "scored": False})
            continue
        f = feature_matrix(series[None, :], np.array([float(emi)]))
        rows.append({"vendor_id": vid, "scored": True, **{k: float(f[k][0]) for k in FEATURE_NAMES + ["income_to_emi"]}})
    out = pd.DataFrame(rows)
    ok = out.scored.to_numpy()
    out["pd"] = np.nan
    out.loc[ok, "pd"] = scorer.predict_pd(out.loc[ok, FEATURE_NAMES].to_numpy())
    out["score"] = np.where(ok, pd_to_score(out["pd"].fillna(0.5).to_numpy()), np.nan)
    out["model_band"] = np.where(ok, score_to_band(out["score"].fillna(300).to_numpy()), "not_scored")
    k = load_config()["baseline_rule"]["min_income_to_emi"]
    out["baseline_decision"] = np.where(~ok, "not_scored", np.where(out.get("income_to_emi", 0) >= k, "approve", "decline"))
    return out


def shadow_report(loans: pd.DataFrame, daily: pd.DataFrame, scorer: CashFlowScorer | None = None) -> dict[str, Any]:
    loans = loans.copy()
    _validate(loans, daily)
    scorer = scorer or CashFlowScorer.load()
    loans["lender_decision"] = loans.lender_decision.astype(str).str.lower()
    if "default_12m" not in loans:
        loans["default_12m"] = pd.NA
    s = score_batch(scorer, loans, daily)
    df = loans.merge(s, on="vendor_id", how="left")
    df = df[df.scored.fillna(False)]
    n_unscored = int(len(loans) - len(df))

    appr = df[df.lender_decision == "approve"]
    known = appr[appr.default_12m.notna()].copy()
    known["default_12m"] = known.default_12m.astype(int)
    y = known.default_12m.to_numpy()

    def rate(x: pd.Series) -> float | None:
        return round(float(x.mean()), 4) if len(x) else None

    def ctab(col: str) -> dict[str, dict[str, int]]:
        t = pd.crosstab(df.lender_decision, df[col])
        return {i: {c: int(t.loc[i, c]) for c in t.columns} for i in t.index}

    def swap_out(decision_col: str, declined_values: list[str]) -> dict[str, Any]:
        removed = known[known[decision_col].isin(declined_values)]
        kept = known[~known[decision_col].isin(declined_values)]
        return {"lender_approvals_this_would_have_declined": int(len(removed)),
                "their_default_rate": rate(removed.default_12m),
                "default_rate_of_the_rest": rate(kept.default_12m),
                "defaults_avoided": int(removed.default_12m.sum()),
                "good_loans_lost": int(len(removed) - removed.default_12m.sum())}

    by_band = [{"band": b, "n": int((known.model_band == b).sum()), "default_rate": rate(known.default_12m[known.model_band == b])}
               for b in ("approve", "review", "decline")]
    declined = df[df.lender_decision == "decline"]
    res: dict[str, Any] = {
        "notice": "Shadow mode: read-only comparison. No real lending decision was changed.",
        "data": "Model built on SYNTHETIC data; treat results as a method check, not evidence of accuracy.",
        "model_version": scorer.model_version,
        "inputs": {"loans": int(len(loans)), "scored": int(len(df)), "not_scored_insufficient_history": n_unscored,
                   "lender_approved": int(len(appr)), "lender_declined": int(len(declined)),
                   "approved_with_known_outcome": int(len(known))},
        "lender": {"approval_rate": rate((df.lender_decision == "approve").astype(int)),
                   "default_rate_of_approvals": rate(known.default_12m)},
        "model": {"band_shares": {b: rate((df.model_band == b).astype(int)) for b in ("approve", "review", "decline")},
                  "default_rate_by_band_among_lender_approvals": by_band,
                  "auc_on_lender_approvals": round(float(roc_auc_score(y, known.pd)), 4) if 0 < y.sum() < len(y) else None,
                  "if_decline_band_applied_to_lender_approvals": swap_out("model_band", ["decline"]),
                  "agreement_with_lender": ctab("model_band")},
        "baseline_rule": {"rule": f"approve if monthly UPI income >= {load_config()['baseline_rule']['min_income_to_emi']} x EMI",
                          "approval_rate": rate((df.baseline_decision == "approve").astype(int)),
                          "auc_on_lender_approvals": round(float(roc_auc_score(y, -known.income_to_emi)), 4) if 0 < y.sum() < len(y) else None,
                          "if_applied_to_lender_approvals": swap_out("baseline_decision", ["decline"]),
                          "agreement_with_lender": ctab("baseline_decision")},
        "lender_declines": {
            "count": int(len(declined)),
            "model_would_approve": int((declined.model_band == "approve").sum()),
            "model_would_review": int((declined.model_band == "review").sum()),
            "baseline_would_approve": int((declined.baseline_decision == "approve").sum()),
            "note": "Outcomes are unknown for loans the lender declined, so these cannot be scored as right or wrong. "
                    "They are candidates for a controlled test, not proof of missed good borrowers.",
        },
    }
    return res


def to_markdown(r: dict[str, Any]) -> str:
    i, m, b, ld = r["inputs"], r["model"], r["baseline_rule"], r["lender_declines"]
    ms, bs = m["if_decline_band_applied_to_lender_approvals"], b["if_applied_to_lender_approvals"]
    L = ["# Shadow-mode report", "", f"> {r['notice']}", f"> {r['data']}", "",
         f"Loans: {i['loans']} ({i['scored']} scored, {i['not_scored_insufficient_history']} with too little history). "
         f"Lender approved {i['lender_approved']}, declined {i['lender_declined']}; outcomes known for {i['approved_with_known_outcome']}.", "",
         "## Among loans the lender approved", "",
         f"Lender's default rate on approvals: **{r['lender']['default_rate_of_approvals']:.2%}**", "",
         "| | would decline | their default rate | rest's default rate | defaults avoided | good loans lost | AUC |",
         "|---|---|---|---|---|---|---|",
         f"| Model (decline band) | {ms['lender_approvals_this_would_have_declined']} | {ms['their_default_rate'] or 0:.2%} | "
         f"{ms['default_rate_of_the_rest'] or 0:.2%} | {ms['defaults_avoided']} | {ms['good_loans_lost']} | {m['auc_on_lender_approvals']} |",
         f"| Baseline rule | {bs['lender_approvals_this_would_have_declined']} | {bs['their_default_rate'] or 0:.2%} | "
         f"{bs['default_rate_of_the_rest'] or 0:.2%} | {bs['defaults_avoided']} | {bs['good_loans_lost']} | {b['auc_on_lender_approvals']} |",
         "", "Default rate by model band (lender approvals only):", ""]
    for row in m["default_rate_by_band_among_lender_approvals"]:
        L.append(f"* {row['band']}: n={row['n']}, default rate {row['default_rate'] if row['default_rate'] is not None else '-'}")
    L += ["", "## Loans the lender declined", "",
          f"{ld['count']} declined. The model would have put {ld['model_would_approve']} in approve and "
          f"{ld['model_would_review']} in review; the baseline rule would have approved {ld['baseline_would_approve']}.",
          "", f"_{ld['note']}_", ""]
    return "\n".join(L)


def report_from_csv_text(loans_csv: str, daily_csv: str) -> dict[str, Any]:
    loans = pd.read_csv(io.StringIO(loans_csv))
    daily = pd.read_csv(io.StringIO(daily_csv))
    return shadow_report(loans, daily)


def run() -> dict[str, Any]:
    ensure_dirs()
    loans, daily = make_sample_inputs()
    loans.to_csv(DATA_DIR / "shadow_loans_sample.csv", index=False)
    daily.to_csv(DATA_DIR / "shadow_daily_sample.csv", index=False)
    before = loans.copy()
    r = shadow_report(loans, daily)
    assert loans.equals(before), "shadow mode must not modify the input"
    (REPORT_DIR / "shadow_report.json").write_text(json.dumps(r, indent=2))
    (REPORT_DIR / "shadow_report.md").write_text(to_markdown(r))
    log.info("shadow report written: lender approvals default rate %s", r["lender"]["default_rate_of_approvals"])
    return r


if __name__ == "__main__":
    run()
