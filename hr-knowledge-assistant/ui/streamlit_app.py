"""Streamlit chat UI. It is a thin client: all logic lives in the FastAPI backend,
so the same API can also serve the React UI, Slack/Teams bots, etc.

Run:  streamlit run ui/streamlit_app.py   (API_URL defaults to http://localhost:8000)
"""
import json
import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
STEP_LABELS = {
    "route": "Understanding your question",
    "rewrite": "Rewriting follow-up into a standalone query",
    "retrieve": "Searching HR policies (hybrid: semantic + keyword)",
    "grade": "Checking the policies actually answer it",
    "generate": "Writing a grounded answer",
    "leave_balance": "Looking up your leave balance in the HR system",
    "escalate": "Raising a ticket with your HR Business Partner",
    "chitchat": "Replying",
}

st.set_page_config(page_title="Nimbus HR Assistant", page_icon="💬", layout="centered")


def stream_chat(question: str, employee_id: str, session_id: str):
    """Parse the Server-Sent Events stream from /chat/stream."""
    with requests.post(
        f"{API_URL}/chat/stream",
        json={"question": question, "employee_id": employee_id, "session_id": session_id},
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        event = None
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                yield event, json.loads(line.split(":", 1)[1].strip())


def render_sources(sources: list[dict]):
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            st.markdown(f"**[{s['id']}] {s['source']}** — {s.get('section') or ''}  `score={s.get('score')}`")
            if s.get("text"):
                st.caption(s["text"][:600])


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Nimbus HR Assistant")
    employee_id = st.selectbox("Signed in as (demo SSO)", ["E1001", "E1002", "E1003"])
    try:
        emp = requests.get(f"{API_URL}/employees/{employee_id}", timeout=5).json()
        st.caption(f"{emp['name']} · {emp['department']} · HRBP: {emp['hrbp']}")
        ready = requests.get(f"{API_URL}/ready", timeout=5).json()
        st.success(f"API ready · LLM: {ready['llm_provider']} · {ready['chunks']} chunks indexed")
    except Exception as e:  # noqa: BLE001
        st.error(f"API not reachable at {API_URL}: {e}")
    show_debug = st.toggle("Show agent steps", value=True)
    if st.button("New conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = uuid.uuid4().hex
        st.rerun()
    st.divider()
    st.markdown("**Try asking**")
    examples = [
        "How many sick leaves do I get?",
        "Can I carry it forward?",
        "What is my leave balance?",
        "What is the hotel limit in metro cities?",
        "Do we get stock options?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
    st.session_state.messages = []

st.title("💬 Ask HR")
st.caption("Answers are grounded in Nimbus HR policies, with citations. Unknown questions are escalated to HR.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        render_sources(m.get("sources", []))

question = st.chat_input("Ask about leave, benefits, onboarding, WFH, expenses…") or st.session_state.pop("pending", None)
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        status = st.status("Thinking…", expanded=show_debug) if show_debug else None
        placeholder = st.empty()
        text, final = "", {}
        try:
            for event, data in stream_chat(question, employee_id, st.session_state.session_id):
                if event == "step" and status:
                    status.write(STEP_LABELS.get(data["node"], data["node"]))
                elif event == "token":
                    text += data["text"]
                    placeholder.markdown(text + "▌")
                elif event == "final":
                    final = data
        except Exception as e:  # noqa: BLE001
            final = {"answer": f"Sorry, something went wrong: {e}", "sources": []}
        if status:
            label = f"Route: {final.get('route')}"
            if final.get("search_query") and final.get("search_query") != question:
                label += f" · searched for: “{final['search_query']}”"
            status.update(label=label, state="complete", expanded=False)
        answer = final.get("answer") or text
        placeholder.markdown(answer)
        render_sources(final.get("sources", []))
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": final.get("sources", [])})
