"""Phase 3: hold-out evaluation, baseline comparison, bootstrap CI, segment report.

All results are on SYNTHETIC data. They show the method works end to end; they are
not evidence of real-world accuracy.

Run: python -m vendorscore.evaluate   (writes reports/evaluation.json and .md)
"""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve

from vendorscore.config import REPORT_DIR, ensure_dirs, load_config
from vendorscore.data.synth import load_tables
from vendorscore.features import FEATURE_NAMES
from vendorscore.logging_setup import get_logger
from vendorscore.model import CashFlowScorer, build_dataset, pd_to_score, score_to_band, split

log = get_logger(__name__)

INCOME_BANDS = [0, 15000, 30000, 60000, np.inf]
INCOME_LABELS = ["< Rs 15k/month", "Rs 15-30k", "Rs 30-60k", ">= Rs 60k"]


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def ks_stat(y: np.ndarray, p: np.ndarray) -> float:
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def calibration_by_decile(y: np.ndarray, p: np.ndarray) -> list[dict[str, float]]:
    order = np.argsort(p)
    out = []
    for i, idx in enumerate(np.array_split(order, 10)):
        out.append({"decile": i + 1, "n": int(len(idx)), "mean_predicted_pd": round(float(p[idx].mean()), 4),
                    "observed_default_rate": round(float(y[idx].mean()), 4)})
    return out


def approval_curve(y: np.ndarray, risk: np.ndarray, steps: int = 20) -> list[dict[str, float]]:
    """Approve the lowest-risk share r of applicants; report default rate among approved."""
    order = np.argsort(risk, kind="stable")
    n = len(y)
    out = []
    for k in range(1, steps + 1):
        r = k / steps
        m = max(1, int(round(r * n)))
        out.append({"approval_rate": round(r, 3), "default_rate_approved": round(float(y[order[:m]].mean()), 4)})
    return out


def default_at_approval_rate(y: np.ndarray, risk: np.ndarray, rate: float) -> float:
    m = max(1, int(round(rate * len(y))))
    return float(y[np.argsort(risk, kind="stable")[:m]].mean())


def approval_at_default_rate(y: np.ndarray, risk: np.ndarray, max_default: float) -> float:
    ys = y[np.argsort(risk, kind="stable")]
    cum = np.cumsum(ys) / np.arange(1, len(ys) + 1)
    ok = np.where(cum <= max_default + 1e-12)[0]
    return float((ok.max() + 1) / len(ys)) if len(ok) else 0.0


def bootstrap_auc_gain(y: np.ndarray, a: np.ndarray, b: np.ndarray, n_boot: int, seed: int) -> dict[str, float]:
    """Paired bootstrap of AUC(a) - AUC(b) on the same resampled test rows."""
    rng = np.random.default_rng(seed)
    n = len(y)
    gains = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if y[idx].min() == y[idx].max():
            continue
        gains.append(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx]))
    g = np.array(gains)
    return {"gain": round(float(roc_auc_score(y, a) - roc_auc_score(y, b)), 4),
            "ci95_low": round(float(np.percentile(g, 2.5)), 4),
            "ci95_high": round(float(np.percentile(g, 97.5)), 4),
            "n_boot": int(len(g))}


def metric_block(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {"auc": round(float(roc_auc_score(y, p)), 4), "ks": round(ks_stat(y, p), 4),
            "brier": round(float(brier_score_loss(y, p)), 4)}


# --------------------------------------------------------------------------- #
# Main evaluation
# --------------------------------------------------------------------------- #
def evaluate(tables: dict[str, pd.DataFrame] | None = None, scorer: CashFlowScorer | None = None) -> dict[str, Any]:
    cfg = load_config()
    tables = tables or load_tables()
    scorer = scorer or CashFlowScorer.load()
    df = build_dataset(tables)
    train, test = split(df)
    y = test.default_12m.to_numpy()
    X_te = test[FEATURE_NAMES].to_numpy()

    p_lr = scorer.predict_pd(X_te)
    scores = pd_to_score(p_lr)
    bands = score_to_band(scores)

    gbm = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                         l2_regularization=1.0, random_state=cfg["seed"])
    gbm.fit(train[FEATURE_NAMES].to_numpy(), train.default_12m.to_numpy())
    p_gbm = gbm.predict_proba(X_te)[:, 1]

    # ---- baseline rule ------------------------------------------------------
    k = cfg["baseline_rule"]["min_income_to_emi"]
    ratio = test.income_to_emi.to_numpy()
    base_approve = ratio >= k
    base_rate = float(base_approve.mean())
    base_dr = float(y[base_approve].mean())
    base_risk_binary = (~base_approve).astype(float)        # rule as a 0/1 risk score
    base_risk_cont = -ratio                                  # the ratio itself as a ranking

    model_dr_same_rate = default_at_approval_rate(y, p_lr, base_rate)
    model_rate_same_dr = approval_at_default_rate(y, p_lr, base_dr)
    nb = cfg["evaluation"]["n_bootstrap"]

    res: dict[str, Any] = {
        "data": "SYNTHETIC - not evidence of real-world accuracy",
        "model_version": scorer.model_version,
        "n_test": int(len(y)), "test_default_rate": round(float(y.mean()), 4),
        "logistic_regression": {**metric_block(y, p_lr), "coefficients": dict(zip(scorer.feature_names, scorer.coef)),
                                "C": scorer.C},
        "gradient_boosting_comparison": {**metric_block(y, p_gbm),
                                         "note": "comparison only; not used for decisions"},
        "baseline_rule": {
            "rule": f"approve if monthly UPI income >= {k} x EMI",
            "approval_rate": round(base_rate, 4),
            "default_rate_approved": round(base_dr, 4),
            "auc_rule_as_binary": round(float(roc_auc_score(y, base_risk_binary)), 4),
            "auc_ratio_as_ranking": round(float(roc_auc_score(y, base_risk_cont)), 4),
        },
        "vs_baseline": {
            "same_approval_rate": {
                "approval_rate": round(base_rate, 4),
                "baseline_default_rate": round(base_dr, 4),
                "model_default_rate": round(model_dr_same_rate, 4),
                "relative_reduction": round(1 - model_dr_same_rate / base_dr, 4) if base_dr else None,
            },
            "same_default_rate": {
                "default_rate": round(base_dr, 4),
                "baseline_approval_rate": round(base_rate, 4),
                "model_approval_rate": round(model_rate_same_dr, 4),
                "extra_approvals_per_1000_applicants": int(round((model_rate_same_dr - base_rate) * 1000)),
            },
            "auc_gain_vs_rule_binary": bootstrap_auc_gain(y, p_lr, base_risk_binary, nb, cfg["seed"]),
            "auc_gain_vs_ratio_ranking": bootstrap_auc_gain(y, p_lr, base_risk_cont, nb, cfg["seed"]),
            "gbm_auc_gain_vs_lr": bootstrap_auc_gain(y, p_gbm, p_lr, nb, cfg["seed"]),
        },
        "calibration_by_decile": calibration_by_decile(y, p_lr),
        "approval_vs_default_curve": {
            "model": approval_curve(y, p_lr),
            "ratio_ranking_baseline": approval_curve(y, base_risk_cont),
            "baseline_rule_point": {"approval_rate": round(base_rate, 4), "default_rate_approved": round(base_dr, 4)},
        },
        "bands": band_table(y, scores, bands),
        "score_distribution": np.histogram(scores, bins=np.arange(300, 925, 25))[0].tolist(),
    }
    res["segments"] = segment_report(test, y, p_lr, bands, res["logistic_regression"]["auc"], cfg)
    res["bias_check_cash_share"] = cash_share_check(test, tables["hidden_traits"], y, bands)
    return res


def band_table(y: np.ndarray, scores: np.ndarray, bands: np.ndarray) -> list[dict[str, Any]]:
    out = []
    for b in ("approve", "review", "decline"):
        m = bands == b
        out.append({"band": b, "share": round(float(m.mean()), 4), "n": int(m.sum()),
                    "default_rate": round(float(y[m].mean()), 4) if m.any() else None,
                    "score_min": int(scores[m].min()) if m.any() else None,
                    "score_max": int(scores[m].max()) if m.any() else None})
    return out


def segment_report(test: pd.DataFrame, y: np.ndarray, p: np.ndarray, bands: np.ndarray, overall_auc: float,
                   cfg: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    gap = cfg["evaluation"]["weak_segment_auc_gap"]
    min_bads = cfg["evaluation"]["min_bads_for_segment"]
    income_band = pd.cut(test.monthly_upi_income, INCOME_BANDS, labels=INCOME_LABELS, right=False).astype(str)

    def rows(groups: pd.Series, order: list[str] | None = None) -> list[dict[str, Any]]:
        out = []
        for g in order or sorted(groups.unique()):
            m = (groups == g).to_numpy()
            bads = int(y[m].sum())
            auc = round(float(roc_auc_score(y[m], p[m])), 4) if 0 < bads < m.sum() else None
            appr = bands[m] == "approve"
            flags = []
            if bads < min_bads:
                flags.append(f"only {bads} defaults: too few to judge")
            if auc is not None and auc < overall_auc - gap:
                flags.append(f"AUC {auc} is more than {gap} below overall {overall_auc}")
            out.append({"segment": g, "n": int(m.sum()), "defaults": bads,
                        "default_rate": round(float(y[m].mean()), 4), "auc": auc,
                        "approve_share": round(float(appr.mean()), 4),
                        "default_rate_in_approve_band": round(float(y[m][appr].mean()), 4) if appr.any() else None,
                        "flags": flags, "weak": bool(flags)})
        return out

    return {"vendor_type": rows(test.vendor_type), "income_band": rows(income_band, [x for x in INCOME_LABELS if x in set(income_band)])}


def cash_share_check(test: pd.DataFrame, hidden: pd.DataFrame, y: np.ndarray, bands: np.ndarray) -> list[dict[str, Any]]:
    """Synthetic-only: are cash-heavy sellers under-approved relative to their true risk?"""
    cs = test[["vendor_id"]].merge(hidden[["vendor_id", "cash_share"]], on="vendor_id").cash_share.to_numpy()
    cuts = [0, 0.4, 0.6, 1.01]
    labels = ["cash < 40%", "cash 40-60%", "cash > 60%"]
    out = []
    for lo, hi, lab in zip(cuts, cuts[1:], labels):
        m = (cs >= lo) & (cs < hi)
        out.append({"segment": lab, "n": int(m.sum()), "actual_default_rate": round(float(y[m].mean()), 4),
                    "approve_share": round(float((bands[m] == "approve").mean()), 4),
                    "decline_share": round(float((bands[m] == "decline").mean()), 4)})
    return out


# --------------------------------------------------------------------------- #
# Markdown report
# --------------------------------------------------------------------------- #
def to_markdown(r: dict[str, Any]) -> str:
    lr, gb, bl, vs = r["logistic_regression"], r["gradient_boosting_comparison"], r["baseline_rule"], r["vs_baseline"]
    L = ["# Evaluation report (SYNTHETIC DATA)", "",
         "> All numbers come from synthetic data. They show the pipeline works; they are **not** real-world accuracy.", "",
         f"Test set: {r['n_test']} vendors, default rate {r['test_default_rate']:.1%}.", "",
         "## Headline metrics", "", "| model | AUC | KS | Brier |", "|---|---|---|---|",
         f"| Logistic regression (decision model) | {lr['auc']} | {lr['ks']} | {lr['brier']} |",
         f"| Gradient boosting (comparison only) | {gb['auc']} | {gb['ks']} | {gb['brier']} |",
         f"| Baseline rule as 0/1 | {bl['auc_rule_as_binary']} | - | - |",
         f"| Baseline ratio as a ranking | {bl['auc_ratio_as_ranking']} | - | - |", "",
         "## Against the baseline rule", "", f"Rule: **{bl['rule']}**. It approves {bl['approval_rate']:.1%} "
         f"with {bl['default_rate_approved']:.2%} defaults among approved.", ""]
    s1, s2 = vs["same_approval_rate"], vs["same_default_rate"]
    L += [f"* **Same approval rate ({s1['approval_rate']:.1%})**: model default rate {s1['model_default_rate']:.2%} vs "
          f"baseline {s1['baseline_default_rate']:.2%} (relative reduction {s1['relative_reduction']:.0%}).",
          f"* **Same default rate ({s2['default_rate']:.2%})**: model approves {s2['model_approval_rate']:.1%} vs "
          f"baseline {s2['baseline_approval_rate']:.1%} ({s2['extra_approvals_per_1000_applicants']:+d} per 1,000 applicants).",
          ""]
    for k, lab in [("auc_gain_vs_rule_binary", "vs the 0/1 rule"), ("auc_gain_vs_ratio_ranking", "vs ranking by the ratio alone"),
                   ("gbm_auc_gain_vs_lr", "gradient boosting minus logistic regression")]:
        g = vs[k]
        L.append(f"* AUC gain {lab}: **{g['gain']:+.4f}** (95% bootstrap CI {g['ci95_low']:+.4f} to {g['ci95_high']:+.4f}, {g['n_boot']} resamples)")
    L += ["", "## Bands", "", "| band | share | default rate | score range |", "|---|---|---|---|"]
    for b in r["bands"]:
        L.append(f"| {b['band']} | {b['share']:.1%} | {b['default_rate']:.2%} | {b['score_min']}-{b['score_max']} |")
    L += ["", "## Calibration by decile", "", "| decile | predicted PD | observed |", "|---|---|---|"]
    for c in r["calibration_by_decile"]:
        L.append(f"| {c['decile']} | {c['mean_predicted_pd']:.2%} | {c['observed_default_rate']:.2%} |")
    for name, rows in r["segments"].items():
        L += ["", f"## Segments by {name.replace('_', ' ')}", "",
              "| segment | n | defaults | default rate | AUC | approve share | flags |", "|---|---|---|---|---|---|---|"]
        for s in rows:
            L.append(f"| {s['segment']} | {s['n']} | {s['defaults']} | {s['default_rate']:.1%} | {s['auc']} | "
                     f"{s['approve_share']:.1%} | {'; '.join(s['flags']) or '-'} |")
    L += ["", "## Bias check: cash-heavy sellers (synthetic-only, uses a hidden trait)", "",
          "| cash share | n | actual default rate | approve share | decline share |", "|---|---|---|---|---|"]
    for s in r["bias_check_cash_share"]:
        L.append(f"| {s['segment']} | {s['n']} | {s['actual_default_rate']:.1%} | {s['approve_share']:.1%} | {s['decline_share']:.1%} |")
    return "\n".join(L) + "\n"


def run() -> dict[str, Any]:
    ensure_dirs()
    r = evaluate()
    (REPORT_DIR / "evaluation.json").write_text(json.dumps(r, indent=2))
    (REPORT_DIR / "evaluation.md").write_text(to_markdown(r))
    log.info("LR AUC %.4f | GBM AUC %.4f | baseline-rule AUC %.4f", r["logistic_regression"]["auc"],
             r["gradient_boosting_comparison"]["auc"], r["baseline_rule"]["auc_rule_as_binary"])
    return r


if __name__ == "__main__":
    run()
