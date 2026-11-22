"""Phase 4: FastAPI scoring service.

Run: uvicorn vendorscore.api.app:app --port 8000
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from vendorscore import __version__
from vendorscore.api.audit import AuditLog, hash_vendor_id
from vendorscore.api.schemas import DATA_NOTE, DECISION_NOTE, ScoreRequest, ScoreResponse
from vendorscore.config import PROJECT_ROOT, load_config
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


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})
