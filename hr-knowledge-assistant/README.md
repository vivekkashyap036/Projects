# Nimbus HR Knowledge Assistant

An agentic **RAG** chatbot that answers employee questions about HR policies (leave, benefits,
onboarding, WFH, expenses, code of conduct) **with citations**. It looks up personal data like leave
balance in an HR database, and when the policies don't contain the answer it **escalates to a human** by raising a ticket instead of guessing.

**Stack:** Python · FastAPI · LangChain · LangGraph · Chroma (vector DB) · BM25 · FastEmbed embeddings ·
Groq / OpenAI / Azure OpenAI / Gemini / Ollama · SQLAlchemy (SQLite / PostgreSQL) · Streamlit · React ·
Docker · Kubernetes (kind) · pytest

> Company "Nimbus Technologies" and all policy documents are fictional sample data.

---

## Architecture

```
          ┌────────────┐   ┌────────────┐
          │ Streamlit  │   │  React UI  │          (thin clients, SSE streaming)
          └─────┬──────┘   └─────┬──────┘
                └───────┬────────┘
                        ▼  REST + Server-Sent Events
              ┌───────────────────────┐
              │   FastAPI  (app/api)  │  /chat  /chat/stream  /ready  /ingest  /tickets
              └──────────┬────────────┘
                         ▼
         ┌──────────── LangGraph agent (app/graph.py) ────────────┐
         │ route ─┬─► rewrite ─► retrieve ─► grade ─┬─► generate  │
         │        │                                 └─► escalate  │
         │        ├─► leave_balance (SQL tool)                    │
         │        ├─► escalate (create ticket)                    │
         │        └─► chitchat                                    │
         └──────┬───────────────────┬────────────────────┬────────┘
                ▼                   ▼                    ▼
     Hybrid retriever          LLM (any provider     PostgreSQL / SQLite
     Chroma (dense, cosine)    via LangChain)        employees · tickets ·
     + BM25 (sparse), RRF                            chat history
                ▲
     Ingestion (app/ingest.py): load → markdown-header split → recursive split
                                → embed (bge-small) → Chroma
```

### Request flow ("Can I carry it forward?", asked after a question about sick leave)
1. **route**: the LLM classifies the intent → `policy_question`.
2. **rewrite**: uses chat history to make the follow-up standalone → *"Can sick leave be carried forward?"*
3. **retrieve**: hybrid search. Dense vector search (meaning) + BM25 (exact keywords), fused with Reciprocal Rank Fusion → top-4 chunks.
4. **grade**: a cheap score threshold first; if that passes, one LLM call checks whether the context actually answers the question.
5. **generate**: the LLM answers **only** from the numbered context and cites `[1]`, `[2]`; tokens stream to the UI.
6. If grading fails → **escalate**: a ticket is created for the employee's HR Business Partner.

---

## Run it

### Option A: local Python (fastest)
```bash
cd hr-knowledge-assistant
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add GROQ_API_KEY (free at console.groq.com) or another provider's key
python -m app.ingest            # build the vector index
uvicorn app.api:app --reload    # API  -> http://localhost:8000/docs
streamlit run ui/streamlit_app.py   # UI -> http://localhost:8501   (in a second terminal)
```
No API key? It still runs: `LLM_PROVIDER=auto` falls back to an offline **mock** LLM (extractive answers).

Optional React UI: `cd frontend && npm install && npm run dev` → http://localhost:5173

### Option B: docker compose (API + UI + Postgres)
```bash
cp .env.example .env && docker compose up --build
```

### Option C: Kubernetes (kind)
```bash
./scripts/k8s-up.sh        # cluster + build + load image + apply manifests  -> UI at http://localhost:8080
./scripts/k8s-demo.sh      # guided tour: self-healing, scaling, rolling update/rollback, PVC, Job
./scripts/k8s-down.sh
```
See [docs/K8S_GUIDE.md](docs/K8S_GUIDE.md) for what every manifest does.

### Tests and evaluation
```bash
pytest -q                                  # 12 offline tests (mock LLM + hashing embeddings)
python -m eval.evaluate                    # hit@k, MRR, answer accuracy, abstain accuracy on a golden set
```

---

## Project layout
```
app/
  config.py       settings from env (.env / ConfigMap / Secret)
  ingest.py       load → chunk → embed → store
  embeddings.py   FastEmbed / OpenAI / offline hashing embeddings
  retriever.py    hybrid dense + BM25 retrieval with Reciprocal Rank Fusion
  llm.py          provider factory + offline mock LLM
  graph.py        LangGraph agent (routing, rewrite, grading, tools, escalation)
  db.py           SQLAlchemy models: employees, tickets, chat history
  api.py          FastAPI (REST + SSE streaming, health/readiness probes)
ui/streamlit_app.py
frontend/         React (Vite) chat UI
data/policies/    knowledge base (markdown; PDFs also supported)
eval/             golden Q&A set + evaluation script
tests/            pytest suite
k8s/              Kubernetes manifests (kustomize)
scripts/          kind up / demo / down
docs/             interview prep + Kubernetes guide
```

## Key design decisions
| Decision | Why |
|---|---|
| LangGraph state machine, not a single chain | Different intents need different paths (RAG / DB tool / human hand-off); explicit typed state is testable and traceable |
| Hybrid retrieval (dense + BM25 + RRF) | Embeddings capture meaning; BM25 nails acronyms and numbers (POSH, PF, INR 15,000). RRF merges ranks without score normalisation |
| Header-aware chunking + heading prefix | Chunks never mix two policies, and each chunk says what it's about, which improves both retrieval and citations |
| Two-stage grading before answering | Avoids hallucinated answers to out-of-scope questions; cheap threshold first, one LLM call only when needed |
| Leave balance from SQL, not the LLM | Personal numbers must be exact, so the LLM never produces them |
| Chat history in the DB, not in memory | API stays stateless → any replica can serve any request (horizontal scaling in k8s) |
| Provider-agnostic LLM factory + mock | Swap Groq ↔ Azure OpenAI ↔ Gemini via config; tests/CI run offline |
