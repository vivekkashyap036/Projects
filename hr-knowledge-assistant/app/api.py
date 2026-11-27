"""FastAPI backend.

Endpoints
  GET  /health           liveness  - is the process up?          (k8s livenessProbe)
  GET  /ready            readiness - index loaded + DB reachable? (k8s readinessProbe)
  POST /chat             full answer as JSON
  POST /chat/stream      Server-Sent Events: node progress + LLM tokens + final payload
  POST /ingest           rebuild the vector index from DOCS_DIR
  GET  /tickets          HR tickets raised by the assistant
  GET  /employees/{id}   mock HRMS lookup (used by the UI "login")
"""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app import db
from app.config import get_settings
from app.graph import build_graph, history_to_messages
from app.ingest import build_index
from app.llm import get_llm
from app.retriever import HybridRetriever

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hr-api")


class AppState:
    graph = None
    retriever: HybridRetriever | None = None
    provider = ""


state = AppState()


def load_agent() -> None:
    settings = get_settings()
    state.retriever = HybridRetriever(settings)
    if state.retriever.size == 0:
        log.warning("Vector index empty - building it now from %s", settings.docs_dir)
        build_index(settings)
        state.retriever = HybridRetriever(settings)
    state.provider = settings.resolved_llm_provider()
    state.graph = build_graph(settings, get_llm(settings), state.retriever)
    log.info("Agent ready: llm=%s embeddings=%s chunks=%d", state.provider, settings.embedding_provider, state.retriever.size)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    load_agent()
    yield


app = FastAPI(title="Nimbus HR Knowledge Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    employee_id: str = "E1001"
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    route: str
    sources: list[dict]
    session_id: str
    ticket_id: int | None = None
    search_query: str | None = None
    latency_ms: int


def _inputs(req: ChatRequest, session_id: str) -> dict:
    history = history_to_messages(db.load_history(session_id, get_settings().history_window))
    return {"question": req.question.strip(), "employee_id": req.employee_id, "history": history}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        db.ping()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"database not reachable: {e}") from e
    if state.graph is None or not state.retriever or state.retriever.size == 0:
        raise HTTPException(503, "agent not loaded")
    return {"status": "ready", "llm_provider": state.provider, "chunks": state.retriever.size}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.perf_counter()
    session_id = req.session_id or uuid.uuid4().hex
    result = state.graph.invoke(_inputs(req, session_id))
    db.save_message(session_id, "user", req.question)
    db.save_message(session_id, "assistant", result["answer"])
    return ChatResponse(
        answer=result["answer"],
        route=result["route"],
        sources=result.get("sources", []),
        session_id=session_id,
        ticket_id=result.get("ticket_id"),
        search_query=result.get("search_query"),
        latency_ms=int((time.perf_counter() - start) * 1000),
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session_id = req.session_id or uuid.uuid4().hex
    inputs = _inputs(req, session_id)

    async def events():
        final: dict = {}
        # "updates" -> one event per finished node; "messages" -> LLM tokens as they are generated
        async for mode, payload in state.graph.astream(inputs, stream_mode=["updates", "messages"]):
            if mode == "updates":
                for node, update in payload.items():
                    final.update(update or {})
                    yield {"event": "step", "data": json.dumps({"node": node})}
            else:
                chunk, meta = payload
                if meta.get("langgraph_node") in ("generate", "chitchat") and chunk.content:
                    yield {"event": "token", "data": json.dumps({"text": chunk.content})}
        db.save_message(session_id, "user", req.question)
        db.save_message(session_id, "assistant", final.get("answer", ""))
        yield {
            "event": "final",
            "data": json.dumps(
                {
                    "answer": final.get("answer", ""),
                    "route": final.get("route"),
                    "sources": final.get("sources", []),
                    "ticket_id": final.get("ticket_id"),
                    "search_query": final.get("search_query"),
                    "session_id": session_id,
                }
            ),
        }

    return EventSourceResponse(events())


@app.post("/ingest")
def ingest():
    n = build_index(get_settings())
    load_agent()
    return {"indexed_chunks": n}


@app.get("/tickets")
def tickets(employee_id: str | None = None):
    return [
        {"id": t.id, "employee_id": t.employee_id, "question": t.question, "status": t.status, "created_at": t.created_at.isoformat()}
        for t in db.list_tickets(employee_id)
    ]


@app.get("/employees/{employee_id}")
def employee(employee_id: str):
    emp = db.get_employee(employee_id)
    if not emp:
        raise HTTPException(404, "employee not found")
    return {"id": emp.id, "name": emp.name, "department": emp.department, "hrbp": emp.hrbp}
