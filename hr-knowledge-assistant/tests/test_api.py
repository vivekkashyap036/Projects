import json

from fastapi.testclient import TestClient

from app.api import app


def test_endpoints():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        ready = client.get("/ready").json()
        assert ready["status"] == "ready" and ready["chunks"] > 0

        r = client.post("/chat", json={"question": "What is the gym reimbursement?", "employee_id": "E1003"}).json()
        assert "1,000" in r["answer"] and r["route"] == "policy_question"

        # same session -> history is used for the follow-up
        sid = r["session_id"]
        r2 = client.post("/chat", json={"question": "Is it monthly?", "employee_id": "E1003", "session_id": sid}).json()
        assert r2["search_query"] != "Is it monthly?"

        assert client.post("/chat", json={"question": ""}).status_code == 422
        assert client.get("/employees/NOPE").status_code == 404


def test_streaming_endpoint_emits_steps_tokens_and_final():
    with TestClient(app) as client:
        with client.stream("POST", "/chat/stream", json={"question": "How many public holidays are there?"}) as resp:
            body = "".join(resp.iter_text())
    events = [l.split(":", 1)[1].strip() for l in body.splitlines() if l.startswith("event:")]
    assert events[0] == "step" and "token" in events and events[-1] == "final"
    final = json.loads([l for l in body.splitlines() if l.startswith("data:")][-1][5:])
    assert "12 public holidays" in final["answer"]
