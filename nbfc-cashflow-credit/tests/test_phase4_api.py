"""Phase 4: API contract, consent rejection, minimum history, audit log, determinism."""
from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from vendorscore.api import app as app_mod
from vendorscore.api.audit import AuditLog, hash_vendor_id


@pytest.fixture()
def client(tmp_path, trained):
    scorer, _, _ = trained
    model_path = tmp_path / "model.json"
    scorer.save(model_path)
    app_mod.init_state(model_path=model_path, audit_path=tmp_path / "audit.jsonl")
    with TestClient(app_mod.app) as c:
        yield c


def _payload(days=120, consent=True, level=1200.0, vid="VENDOR-123"):
    rng = np.random.default_rng(3)
    recs = [{"day": d, "n_txn": 20, "inflow": float(round(level * np.exp(rng.normal(0, 0.3)), 0))} for d in range(days)]
    return {"vendor_id": vid, "consent_given": consent,
            "loan": {"amount": 30000, "tenure_months": 12, "emi": 2900}, "daily_records": recs}


def test_health_and_model_info(client):
    h = client.get("/health").json()
    assert h["model_loaded"] is True
    info = client.get("/model-info").json()
    assert len(info["features"]) == 5
    assert info["bands"]["approve_min"] > info["bands"]["decline_below"]
    assert "synthetic" in info["data_note"].lower()


def test_score_contract(client):
    r = client.post("/score", json=_payload())
    assert r.status_code == 200
    body = r.json()
    for k in ("probability_of_default", "score", "band", "human_review_required", "reasons", "strengths",
              "model_version", "decision_note", "request_id"):
        assert k in body
    assert 300 <= body["score"] <= 900
    assert body["band"] in {"approve", "review", "decline"}
    assert body["human_review_required"] == (body["band"] != "approve")
    assert body["days_used"] == 120


def test_consent_false_is_rejected(client):
    r = client.post("/score", json=_payload(consent=False))
    assert r.status_code == 403
    assert r.json()["code"] == "CONSENT_REQUIRED"
    assert "score" not in r.json()


def test_fewer_than_90_days_rejected(client):
    r = client.post("/score", json=_payload(days=89))
    assert r.status_code == 422
    assert r.json()["code"] == "INSUFFICIENT_HISTORY"
    assert client.post("/score", json=_payload(days=90)).status_code == 200


def test_bad_input_rejected(client):
    p = _payload()
    p["loan"] = {"amount": 30000, "tenure_months": 12}
    assert client.post("/score", json=p).status_code == 422
    p = _payload()
    p["daily_records"][0]["inflow"] = -5
    assert client.post("/score", json=p).status_code == 422


def test_emi_from_rate(client):
    p = _payload()
    p["loan"] = {"amount": 12000, "tenure_months": 12, "annual_rate": 0.24}
    assert abs(client.post("/score", json=p).json()["emi_used"] - 1135) <= 1


def test_audit_log_hashes_id_and_chains(client, tmp_path):
    client.post("/score", json=_payload(vid="SECRET-ID-9"))
    client.post("/score", json=_payload(vid="SECRET-ID-9", consent=False))
    raw = (tmp_path / "audit.jsonl").read_text()
    assert "SECRET-ID-9" not in raw
    lines = [json.loads(x) for x in raw.splitlines()]
    assert lines[-2]["request"]["vendor_hash"] == hash_vendor_id("SECRET-ID-9")
    assert lines[-1]["event"] == "score_rejected" and lines[-1]["status"] == 403
    assert all(l["model_version"] for l in lines)
    assert "daily_records" not in raw  # raw income data is not stored
    ok, n = AuditLog(tmp_path / "audit.jsonl").verify_chain()
    assert ok and n == len(lines)


def test_audit_tamper_detected(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    for i in range(3):
        log.append("score", {"i": i})
    lines = (tmp_path / "a.jsonl").read_text().splitlines()
    lines[1] = lines[1].replace('"i": 1', '"i": 7')
    (tmp_path / "a.jsonl").write_text("\n".join(lines) + "\n")
    assert log.verify_chain()[0] is False


def test_api_scoring_is_deterministic(client):
    a = client.post("/score", json=_payload()).json()
    b = client.post("/score", json=_payload()).json()
    a.pop("request_id"), b.pop("request_id")
    assert a == b


def test_explain_endpoint_uses_only_score_output(client, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    body = client.post("/score", json=_payload(vid="HIDDEN-55")).json()
    r = client.post("/explain", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["source"] == "template" and out["validator"]["ok"]
    assert "HIDDEN-55" not in json.dumps(out["llm_input"])
    assert str(body["score"]) in out["en"]
