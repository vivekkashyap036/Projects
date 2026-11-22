"""Phase 4: FastAPI scoring service.

Run: uvicorn vendorscore.api.app:app --port 8000
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import numpy as np
import json
import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from vendorscore import __version__
from vendorscore.api.audit import AuditLog, hash_vendor_id
from vendorscore.agents.explainer import explain
from vendorscore.api.schemas import DATA_NOTE, DECISION_NOTE, ExplainRequest, ScoreRequest, ScoreResponse
from vendorscore.agents import early_warning as ew
from vendorscore.agents import shadow as shadow_agent
from vendorscore.config import ARTIFACT_DIR, DATA_DIR, PROJECT_ROOT, REPORT_DIR, load_config
from vendorscore.features import FEATURES, records_to_series
from vendorscore.logging_setup import get_logger
from vendorscore.model import MODEL_PATH, CashFlowScorer

log = get_logger("vendorscore.api")


class State:
    scorer: CashFlowScorer | None = None
    audit: AuditLog | None = None


state = State()


def init_state(model_path: Path = MODEL_PATH, audit_path: Path | None = None) -> None:
    cfg = load_config()
    state.audit = AuditLog(audit_path or (PROJECT_ROOT / cfg["audit"]["path"]))
    if Path(model_path).exists():
        state.scorer = CashFlowScorer.load(model_path)
        log.info("loaded model %s", state.scorer.model_version)
    else:
        state.scorer = None
        log.error("model file %s not found; run `python -m vendorscore.model` first", model_path)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if state.audit is None:
        init_state()
    yield


app = FastAPI(
    title="Vendor cash-flow credit score (decision support)",
    version=__version__,
    description=f"{DECISION_NOTE} {DATA_NOTE}",
    lifespan=lifespan,
)


def _audit(event: str, req: ScoreRequest | None, status: int, response: dict[str, Any] | None, **extra: Any) -> None:
    assert state.audit is not None
    summary: dict[str, Any] = {}
    if req is not None:
        days = [r.day for r in req.daily_records]
        summary = {
            "vendor_hash": hash_vendor_id(req.vendor_id),
            "consent_given": req.consent_given,
            "n_records": len(days),
            "day_span": (max(days) - min(days) + 1) if days else 0,
            "loan": req.loan.model_dump(),
        }
    state.audit.append(event, {
        "model_version": state.scorer.model_version if state.scorer else None,
        "status": status,
        "request": summary,
        "response": response,
        **extra,
    })


@app.get("/health")
def health() -> dict[str, Any]:
    ok = state.scorer is not None
    return {"status": "ok" if ok else "model_not_loaded", "model_loaded": ok,
            "model_version": state.scorer.model_version if ok else None}


@app.get("/model-info")
def model_info() -> dict[str, Any]:
    if state.scorer is None:
        raise HTTPException(503, "model not loaded")
    cfg = load_config()
    s = state.scorer
    return {
        "model_version": s.model_version,
        "model_type": "L2-regularised logistic regression with expected-sign constraints",
        "trained_on": s.trained_on,
        "data_note": DATA_NOTE,
        "decision_note": DECISION_NOTE,
        "features": [{"name": f.name, "label": f.label, "expected_effect_on_risk": "+" if f.expected_sign > 0 else "-",
                      "coefficient": c} for f, c in zip(FEATURES, s.coef)],
        "intercept": s.intercept,
        "regularisation_C": s.C,
        "scorecard": cfg["scorecard"],
        "bands": cfg["bands"],
        "min_days": cfg["features"]["min_days"],
        "max_days": cfg["features"]["max_days"],
        "metadata": s.metadata,
    }


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> Any:
    if state.scorer is None:
        raise HTTPException(503, "model not loaded")
    cfg = load_config()["features"]
    if not req.consent_given:
        detail = "Vendor consent is required before any data is scored. Nothing was scored or stored."
        _audit("score_rejected", req, 403, None, reason="no_consent")
        return JSONResponse(status_code=403, content={"detail": detail, "code": "CONSENT_REQUIRED"})
    series = records_to_series([r.model_dump() for r in req.daily_records], max_days=cfg["max_days"])
    if len(series) < cfg["min_days"]:
        detail = f"At least {cfg['min_days']} days of UPI history are needed; got {len(series)}."
        _audit("score_rejected", req, 422, None, reason="insufficient_history")
        return JSONResponse(status_code=422, content={"detail": detail, "code": "INSUFFICIENT_HISTORY"})

    emi = req.loan.resolved_emi()
    out = state.scorer.score_one(np.asarray(series), emi)
    rid = uuid.uuid4().hex
    resp = {"request_id": rid, **out, "emi_used": emi, "days_used": int(len(series)),
            "decision_note": DECISION_NOTE, "data_note": DATA_NOTE}
    _audit("score", req, 200, {k: resp[k] for k in ("request_id", "score", "band", "probability_of_default",
                                                     "human_review_required")} |
           {"reason_codes": [r["code"] for r in out["reasons"]], "strength_codes": [r["code"] for r in out["strengths"]]})
    log.info("scored request %s band=%s score=%s", rid[:8], out["band"], out["score"])
    return resp


@app.post("/explain")
def explain_endpoint(req: ExplainRequest) -> dict[str, Any]:
    """Explanation agent: takes ONLY the /score output and returns English + Hindi text."""
    res = explain(req.model_dump())
    assert state.audit is not None
    state.audit.append("explain", {"model_version": state.scorer.model_version if state.scorer else None,
                                   "status": 200, "request_id": req.request_id, "source": res["source"],
                                   "validator_ok": res["validator"]["ok"]})
    return res


# --------------------------------------------------------------------------- #
# Lender console (UI) and demo endpoints. Demo endpoints read SYNTHETIC data only
# and can be switched off with DEMO_MODE=0.
# --------------------------------------------------------------------------- #
UI_DIR = PROJECT_ROOT / "ui"


def _demo_enabled() -> None:
    if os.environ.get("DEMO_MODE", "1") == "0":
        raise HTTPException(404, "demo endpoints disabled")


@lru_cache(maxsize=1)
def _demo_tables() -> dict[str, pd.DataFrame]:
    from vendorscore.data.synth import load_tables

    return load_tables()


@lru_cache(maxsize=1)
def _test_ids() -> list[str]:
    p = ARTIFACT_DIR / "split.json"
    return json.loads(p.read_text())["test_vendor_ids"] if p.exists() else []


@app.get("/", include_in_schema=False)
def ui_index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@app.get("/demo/vendors")
def demo_vendors(limit: int = Query(60, le=500)) -> list[dict[str, Any]]:
    """A spread of held-out synthetic vendors to try in the console."""
    _demo_enabled()
    t = _demo_tables()
    v = t["vendors"][t["vendors"].vendor_id.isin(set(_test_ids()))]
    v = v.sort_values("vendor_id").groupby("vendor_type", group_keys=False).head(max(1, limit // 6))
    return v[["vendor_id", "vendor_type", "loan_amount", "tenure_months", "emi"]].head(limit).to_dict("records")


@app.get("/demo/vendor/{vendor_id}")
def demo_vendor(vendor_id: str) -> dict[str, Any]:
    """A ready-to-send /score payload built from a synthetic vendor's 180-day observation window."""
    _demo_enabled()
    t = _demo_tables()
    row = t["vendors"][t["vendors"].vendor_id == vendor_id]
    if row.empty:
        raise HTTPException(404, "unknown synthetic vendor")
    r = row.iloc[0]
    d = t["daily_upi"]
    d = d[(d.vendor_id == vendor_id) & (d.day < int(r.origination_day))]
    return {
        "payload": {
            "vendor_id": vendor_id, "consent_given": True, "vendor_type": r.vendor_type,
            "loan": {"amount": int(r.loan_amount), "tenure_months": int(r.tenure_months), "emi": int(r.emi)},
            "daily_records": [{"day": int(a), "n_txn": int(b), "inflow": float(c)} for a, b, c in zip(d.day, d.n_txn, d.inflow)],
        },
        "synthetic_outcome": {"default_12m": int(r.default_12m),
                              "note": "Synthetic ground truth, shown for demo only. A real lender would not know this at decision time."},
    }


@app.get("/ews/queue")
def ews_queue(as_of_day: int = Query(300, ge=200, le=544)) -> dict[str, Any]:
    """Early-warning agent: this week's review queue for held-out synthetic loans."""
    _demo_enabled()
    alerts = ew.run_weekly(_demo_tables(), as_of_day, vendor_ids=_test_ids() or None)
    assert state.audit is not None
    state.audit.append("ews_run", {"model_version": state.scorer.model_version if state.scorer else None,
                                   "status": 200, "as_of_day": as_of_day, "alerts": len(alerts)})
    return {"as_of_day": as_of_day, "alerts": ew.alerts_as_dicts(alerts),
            "note": ew.HUMAN_ONLY}


@app.get("/reports/{name}")
def get_report(name: str) -> Any:
    allowed = {"evaluation", "early_warning", "shadow_report"}
    if name not in allowed:
        raise HTTPException(404, "unknown report")
    p = REPORT_DIR / f"{name}.json"
    if not p.exists():
        raise HTTPException(404, f"report not generated yet; run `make reports`")
    return json.loads(p.read_text())


class ShadowCSV(BaseModel):
    loans_csv: str
    daily_csv: str


@app.post("/shadow/report")
def shadow_from_csv(body: ShadowCSV) -> dict[str, Any]:
    """Shadow mode on uploaded CSV text. Read-only: nothing is changed or stored except an audit entry."""
    try:
        res = shadow_agent.report_from_csv_text(body.loans_csv, body.daily_csv)
    except shadow_agent.ShadowInputError as exc:
        raise HTTPException(422, str(exc)) from exc
    assert state.audit is not None
    state.audit.append("shadow_report", {"model_version": state.scorer.model_version if state.scorer else None,
                                         "status": 200, "loans": res["inputs"]["loans"]})
    return res


@app.get("/shadow/sample.csv")
def shadow_sample(kind: str = Query("loans", pattern="^(loans|daily)$")) -> FileResponse:
    _demo_enabled()
    p = DATA_DIR / f"shadow_{kind}_sample.csv"
    if not p.exists():
        raise HTTPException(404, "run `python -m vendorscore.agents.shadow` first")
    return FileResponse(p, media_type="text/csv", filename=p.name)


@app.get("/audit/tail")
def audit_tail(n: int = Query(30, le=200)) -> dict[str, Any]:
    assert state.audit is not None
    ok, count = state.audit.verify_chain()
    return {"chain_ok": ok, "entries": count, "tail": state.audit.tail(n)[::-1]}


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})
