"""Phase 2: regularised logistic regression scorecard, 300-900 score, bands and reason codes.

The fitted model is stored as plain JSON (means, scales, coefficients), so a
lender's risk team can read every number. No pickles.

Run: python -m vendorscore.model   (trains and writes artifacts/model.json)
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split

from vendorscore.config import ARTIFACT_DIR, ensure_dirs, load_config
from vendorscore.data.synth import load_tables, observation_matrix
from vendorscore.features import EXPECTED_SIGN, FEATURE_NAMES, feature_matrix
from vendorscore.logging_setup import get_logger

log = get_logger(__name__)
MODEL_PATH = ARTIFACT_DIR / "model.json"
SPLIT_PATH = ARTIFACT_DIR / "split.json"


# --------------------------------------------------------------------------- #
# Score scaling and bands
# --------------------------------------------------------------------------- #
def pd_to_score(pd_: np.ndarray | float) -> np.ndarray | float:
    sc = load_config()["scorecard"]
    factor = sc["pdo"] / math.log(2)
    offset = sc["anchor_score"] - factor * math.log(sc["anchor_odds"])
    p = np.clip(np.asarray(pd_, dtype=float), 1e-6, 1 - 1e-6)
    score = offset + factor * np.log((1 - p) / p)
    out = np.clip(np.round(score), sc["min_score"], sc["max_score"])
    return out if out.ndim else float(out)


def score_to_band(score: np.ndarray | float) -> np.ndarray | str:
    b = load_config()["bands"]
    s = np.asarray(score, dtype=float)
    band = np.where(s >= b["approve_min"], "approve", np.where(s < b["decline_below"], "decline", "review"))
    return band if band.ndim else str(band)


# --------------------------------------------------------------------------- #
# Reason codes
# --------------------------------------------------------------------------- #
REASON_CODES: dict[str, tuple[str, str]] = {
    # feature -> (code when it raises risk, code when it lowers risk)
    "log_income_to_emi": ("R01_LOW_INCOME_VS_EMI", "S01_INCOME_COVERS_EMI"),
    "weekly_cv": ("R02_UNEVEN_WEEKLY_INCOME", "S02_STEADY_WEEKLY_INCOME"),
    "longest_dry_spell": ("R03_LONG_GAP_NO_INCOME", "S03_NO_LONG_GAPS"),
    "active_day_share": ("R04_FEW_ACTIVE_DAYS", "S04_REGULAR_ACTIVE_DAYS"),
    "recent_trend": ("R05_RECENT_INCOME_FALL", "S05_RECENT_INCOME_RISE"),
}


def _display_values(raw: dict[str, float]) -> dict[str, Any]:
    trend_pct = int(round((math.exp(raw["recent_trend"]) - 1) * 100))
    return {
        "income_to_emi": round(float(raw["income_to_emi"]), 1),
        "monthly_upi_income": int(round(raw["monthly_upi_income"], -2)),
        "weekly_cv_pct": int(round(raw["weekly_cv"] * 100)),
        "longest_dry_spell": int(raw["longest_dry_spell"]),
        "active_day_pct": int(round(raw["active_day_share"] * 100)),
        "trend_pct": trend_pct,
        "n_days": int(raw["n_days"]),
    }


def reason_text(feature: str, increases_risk: bool, v: dict[str, Any], emi: int) -> tuple[str, str]:
    """Plain-language English and Hindi text. Uses only the displayed numbers."""
    if feature == "log_income_to_emi":
        en = (f"Average monthly UPI income (about Rs {v['monthly_upi_income']}) is {v['income_to_emi']} times the "
              f"EMI of Rs {emi}.")
        hi = (f"औसत मासिक UPI आय (लगभग Rs {v['monthly_upi_income']}) EMI (Rs {emi}) की "
              f"{v['income_to_emi']} गुना है।")
        if increases_risk:
            en += " A larger cushion over the EMI lowers risk."
            hi += " EMI से ज़्यादा आय का अंतर होने पर जोखिम कम होता है।"
    elif feature == "weekly_cv":
        if increases_risk:
            en = f"Weekly UPI income goes up and down a lot (variation of {v['weekly_cv_pct']}%)."
            hi = f"साप्ताहिक UPI आय में काफ़ी उतार-चढ़ाव है ({v['weekly_cv_pct']}% का अंतर)।"
        else:
            en = f"Weekly UPI income is fairly steady (variation of {v['weekly_cv_pct']}%)."
            hi = f"साप्ताहिक UPI आय काफ़ी स्थिर है ({v['weekly_cv_pct']}% का अंतर)।"
    elif feature == "longest_dry_spell":
        if increases_risk:
            en = f"The longest stretch with no UPI income was {v['longest_dry_spell']} days in a row."
            hi = f"सबसे लंबा समय जब कोई UPI आय नहीं आई: लगातार {v['longest_dry_spell']} दिन।"
        else:
            en = f"There were no long gaps in UPI income (longest gap {v['longest_dry_spell']} days)."
            hi = f"UPI आय में कोई लंबा अंतराल नहीं था (सबसे लंबा अंतराल {v['longest_dry_spell']} दिन)।"
    elif feature == "active_day_share":
        if increases_risk:
            en = f"The business was active on only {v['active_day_pct']}% of days; the rest were closures of 2 or more days with no UPI income."
            hi = f"व्यवसाय केवल {v['active_day_pct']}% दिनों में सक्रिय रहा; बाकी दिनों में 2 या ज़्यादा दिन लगातार कोई UPI आय नहीं आई।"
        else:
            en = f"The business was active on {v['active_day_pct']}% of days."
            hi = f"व्यवसाय {v['active_day_pct']}% दिनों में सक्रिय रहा।"
    elif feature == "recent_trend":
        pct = abs(v["trend_pct"])
        if v["trend_pct"] < 0:
            en = f"UPI income in the last 30 days was {pct}% lower than in the 60 days before."
            hi = f"पिछले 30 दिनों की UPI आय उससे पहले के 60 दिनों से {pct}% कम रही।"
        else:
            en = f"UPI income in the last 30 days was {pct}% higher than in the 60 days before."
            hi = f"पिछले 30 दिनों की UPI आय उससे पहले के 60 दिनों से {pct}% ज़्यादा रही।"
    else:  # pragma: no cover
        raise KeyError(feature)
    return en, hi


# --------------------------------------------------------------------------- #
# The scorer
# --------------------------------------------------------------------------- #
@dataclass
class CashFlowScorer:
    feature_names: list[str]
    means: list[float]
    scales: list[float]
    coef: list[float]
    intercept: float
    C: float
    model_version: str
    trained_on: str = "synthetic"
    metadata: dict[str, Any] = field(default_factory=dict)

    # ---- persistence -------------------------------------------------------
    def save(self, path: Path = MODEL_PATH) -> None:
        ensure_dirs()
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "CashFlowScorer":
        return cls(**json.loads(Path(path).read_text()))

    # ---- inference ---------------------------------------------------------
    def _z(self, X: np.ndarray) -> np.ndarray:
        return (X - np.array(self.means)) / np.array(self.scales)

    def predict_pd(self, X: np.ndarray) -> np.ndarray:
        z = self._z(np.atleast_2d(X))
        return 1.0 / (1.0 + np.exp(-(z @ np.array(self.coef) + self.intercept)))

    def contributions(self, X: np.ndarray) -> np.ndarray:
        """Per-feature contribution to the log-odds of default vs an average vendor."""
        return self._z(np.atleast_2d(X)) * np.array(self.coef)

    def score_one(self, inflow: np.ndarray, emi: float, max_reasons: int = 3, max_strengths: int = 2) -> dict[str, Any]:
        feats = feature_matrix(np.asarray(inflow, dtype=float)[None, :], np.array([emi]))
        raw = {k: float(v[0]) for k, v in feats.items()}
        X = np.array([[raw[f] for f in self.feature_names]])
        p = float(self.predict_pd(X)[0])
        score = int(pd_to_score(p))
        band = str(score_to_band(score))
        contrib = self.contributions(X)[0]
        disp = _display_values(raw)
        order = np.argsort(-contrib)
        reasons, strengths = [], []
        for j in order:
            f = self.feature_names[j]
            c = float(contrib[j])
            inc = c > 0
            en, hi = reason_text(f, inc, disp, int(round(emi)))
            item = {
                "code": REASON_CODES[f][0 if inc else 1],
                "feature": f,
                "direction": "increases_risk" if inc else "reduces_risk",
                "impact_points": int(round(-c * load_config()["scorecard"]["pdo"] / math.log(2))),
                "text_en": en,
                "text_hi": hi,
            }
            if inc and c > 0.05 and len(reasons) < max_reasons:
                reasons.append(item)
        for j in order[::-1]:
            f = self.feature_names[j]
            c = float(contrib[j])
            if c < -0.05 and len(strengths) < max_strengths:
                en, hi = reason_text(f, False, disp, int(round(emi)))
                strengths.append({
                    "code": REASON_CODES[f][1], "feature": f, "direction": "reduces_risk",
                    "impact_points": int(round(-c * load_config()["scorecard"]["pdo"] / math.log(2))),
                    "text_en": en, "text_hi": hi,
                })
        return {
            "probability_of_default": round(p, 4),
            "score": score,
            "band": band,
            "human_review_required": band != "approve",
            "reasons": reasons,
            "strengths": strengths,
            "features": {k: round(raw[k], 4) for k in self.feature_names},
            "key_values": disp,
            "model_version": self.model_version,
        }


# --------------------------------------------------------------------------- #
# Training
# --------------------------------------------------------------------------- #
def build_dataset(tables: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    """One row per vendor: features from the 180-day observation window + label + segments."""
    tables = tables or load_tables()
    v = tables["vendors"].reset_index(drop=True)
    obs = int(v.origination_day.iloc[0])
    inflow = observation_matrix(tables["daily_upi"], v.vendor_id.to_numpy(), 0, obs)
    feats = feature_matrix(inflow, v.emi.to_numpy())
    df = v.copy()
    for k, arr in feats.items():
        df[k] = arr
    return df


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = load_config()
    tr, te = train_test_split(df, test_size=cfg["model"]["test_size"], random_state=cfg["seed"],
                              stratify=df["default_12m"])
    return tr.reset_index(drop=True), te.reset_index(drop=True)


def fit_sign_constrained_logreg(Z: np.ndarray, y: np.ndarray, C: float, signs: np.ndarray) -> tuple[np.ndarray, float]:
    """L2-regularised logistic regression with each coefficient kept on its expected side of zero.

    Objective (same convention as scikit-learn): C * sum(logloss) + 0.5 * ||w||^2.
    The bound is a guardrail: a scorecard must never reward, say, more dry days.
    If a bound is active (coefficient pinned at 0) the sign test fails loudly.
    """
    n, k = Z.shape

    def obj(theta: np.ndarray) -> tuple[float, np.ndarray]:
        w, b = theta[:k], theta[k]
        m = Z @ w + b
        p = 1.0 / (1.0 + np.exp(-m))
        ll = np.sum(np.logaddexp(0.0, m) - y * m)
        g = p - y
        grad = np.concatenate([C * (Z.T @ g) + w, [C * g.sum()]])
        return C * ll + 0.5 * float(w @ w), grad

    bounds = [(0.0, None) if s > 0 else (None, 0.0) for s in signs] + [(None, None)]
    x0 = np.zeros(k + 1)
    x0[k] = math.log(y.mean() / (1 - y.mean()))
    res = minimize(obj, x0, jac=True, method="L-BFGS-B", bounds=bounds, options={"maxiter": 5000, "gtol": 1e-8})
    if not res.success:  # pragma: no cover
        log.warning("optimiser: %s", res.message)
    return res.x[:k], float(res.x[k])


def fit_logreg(train: pd.DataFrame) -> CashFlowScorer:
    cfg = load_config()
    X = train[FEATURE_NAMES].to_numpy()
    y = train["default_12m"].to_numpy().astype(float)
    signs = np.array([EXPECTED_SIGN[f] for f in FEATURE_NAMES])
    means, scales = X.mean(axis=0), X.std(axis=0)
    Z = (X - means) / scales
    cv = StratifiedKFold(cfg["model"]["cv_folds"], shuffle=True, random_state=cfg["seed"])
    best_C, best_auc = None, -1.0
    for C in cfg["model"]["logreg_C_grid"]:
        aucs = []
        for tr_i, va_i in cv.split(Z, y):
            w, b = fit_sign_constrained_logreg(Z[tr_i], y[tr_i], C, signs)
            aucs.append(roc_auc_score(y[va_i], Z[va_i] @ w + b))
        auc = float(np.mean(aucs))
        log.info("C=%-5s cv AUC=%.4f", C, auc)
        if auc > best_auc + 1e-4:
            best_C, best_auc = C, auc
    w, b = fit_sign_constrained_logreg(Z, y, best_C, signs)
    m = type("Fitted", (), {"coef_": np.array([w]), "intercept_": np.array([b])})
    scorer = CashFlowScorer(
        feature_names=FEATURE_NAMES,
        means=means.round(6).tolist(),
        scales=scales.round(6).tolist(),
        coef=m.coef_[0].round(6).tolist(),
        intercept=round(float(m.intercept_[0]), 6),
        C=float(best_C),
        model_version=cfg["model_version"],
        metadata={"cv_auc": round(best_auc, 4), "n_train": int(len(train)),
                  "train_default_rate": round(float(y.mean()), 4), "data": "SYNTHETIC"},
    )
    for f, c in zip(FEATURE_NAMES, scorer.coef):
        ok = np.sign(c) == EXPECTED_SIGN[f]
        log.info("coef %-20s %+.4f  expected %+d  %s", f, c, EXPECTED_SIGN[f], "ok" if ok else "SIGN MISMATCH / pinned at 0")
    return scorer


def train() -> CashFlowScorer:
    df = build_dataset()
    tr, te = split(df)
    scorer = fit_logreg(tr)
    scorer.save()
    SPLIT_PATH.write_text(json.dumps({"test_vendor_ids": te.vendor_id.tolist()}))
    log.info("saved %s (C=%s, cv AUC=%s)", MODEL_PATH, scorer.C, scorer.metadata["cv_auc"])
    return scorer


if __name__ == "__main__":
    train()
