# Interview Prep: AI-Powered HR Knowledge Assistant

Goal: be able to explain **every line of this project**, defend every design decision, and handle follow-ups
on RAG, LangChain, LangGraph, LLMs, FastAPI, Streamlit/React, Docker and Kubernetes.

Kubernetes has its own guide: [K8S_GUIDE.md](K8S_GUIDE.md).

---

## 0. Be honest about the project's history (important)

Your resume lists this project with *Python, FastAPI, React.js, RAG, LLMs, LangChain*, and your Zummit
internship mentions contributing to an HR chatbot. Interviewers probe this. A safe, truthful framing:

> "At Zummit I contributed to an early HR chatbot using classic NLP and supervised intent classification.
> Afterwards I built my own **HR Knowledge Assistant** using RAG. Recently I **re-architected it**: I moved
> from a simple LangChain retrieval chain to a **LangGraph agent** with routing, query rewriting, relevance
> grading, a database tool and human escalation. I also added hybrid search, an evaluation set, Docker, and a
> Kubernetes deployment, because my last interview feedback pointed me towards Kubernetes."

That last line turns the feedback into a strength: it shows you act on feedback and learn fast, which is exactly what the JD asks for.
**Only claim what you've actually run.** Run everything in Section 9 yourself before the interview.

---

## 1. Pitches

### 30 seconds
> "It's an HR chatbot that answers employee questions about company policies, such as leave, benefits, onboarding
> and expenses, grounded in the company's own documents and **with citations**. It's a RAG system orchestrated with
> **LangGraph**: it classifies intent, rewrites follow-ups, does hybrid semantic + keyword search, checks that the
> retrieved policy actually answers the question, and only then lets the LLM answer. Personal questions like
> 'what's my leave balance' go to a database tool instead of the LLM, and if the policies don't cover a question
> it raises a ticket to HR instead of hallucinating. FastAPI backend with streaming, Streamlit and React
> front-ends, Postgres, Docker, and deployed on Kubernetes."

### 2 minutes: add the *why*
1. **Problem**: HR teams answer the same questions repeatedly. Policies are long PDFs/wiki pages; employees can't find answers; wrong answers about leave or pay are costly.
2. **Approach**: RAG instead of fine-tuning, because policies change often, we need citations, and RAG needs no training.
3. **Trust**: answer only from retrieved context, cite sources, a relevance gate before answering, escalate when unsure, exact numbers from the DB.
4. **Engineering**: provider-agnostic LLM layer (Groq / OpenAI / Azure OpenAI / Gemini / Ollama), a stateless API with history in Postgres, SSE streaming, tests that run offline, an evaluation harness, Docker and Kubernetes.
5. **Result**: on my golden set of 22 questions I track hit@k, MRR, answer accuracy and abstention accuracy (run `python -m eval.evaluate` with your real key and quote **your** numbers).

---

## 2. Architecture walk-through (draw this on a whiteboard)

```
UI (Streamlit / React) ──HTTP+SSE──► FastAPI ──► LangGraph agent
                                                   route ─► rewrite ─► retrieve ─► grade ─► generate
                                                     │                              └──► escalate (ticket)
                                                     ├─► leave_balance (SQL)
                                                     ├─► escalate
                                                     └─► chitchat
                                     retrieve uses: Chroma (dense) + BM25 (sparse) → RRF
                                     DB: employees, tickets, chat_messages (SQLite / Postgres)
Offline: ingest.py  load → split by markdown headers → recursive split (800/120) → embed (bge-small, 384-d) → Chroma
```

**Key numbers to remember**: 6 policy docs → **37 chunks** · chunk size **800 chars**, overlap **120** ·
embeddings **BAAI/bge-small-en-v1.5, 384 dimensions**, cosine · **top-k = 4** (over-fetch 12 from each retriever) ·
RRF constant **k = 60** · relevance threshold **0.45** (tunable) · history window **6 messages** · **12 tests**.

### Code tour (read in this order)
1. `app/ingest.py`: how documents become chunks + vectors.
2. `app/retriever.py`: hybrid search + RRF (~60 lines; know it cold).
3. `app/graph.py`: the agent; prompts at the top, nodes, then edges.
4. `app/api.py`: endpoints, streaming, readiness.
5. `app/llm.py`: provider factory + the mock.
6. `app/db.py`, `ui/streamlit_app.py`, `frontend/src/api.js`, `tests/`, `eval/`.

---

## 3. RAG concepts (expect deep questions here)

**What is RAG?** Retrieval-Augmented Generation: at question time, *retrieve* relevant passages from your own
knowledge base and put them into the prompt, so the LLM *generates* an answer grounded in them. It fixes three LLM
problems: no knowledge of private data, a stale training cutoff, and hallucination. It also enables citations.

**RAG vs fine-tuning?** Fine-tuning changes *behaviour/style/format*. It is poor at injecting facts that change,
costly to update, and gives no citations. RAG changes *knowledge* at query time: update a document, re-ingest, done.
For HR policies, which change often and need sources, RAG is the right tool. They can be combined.

**The two phases**
- *Indexing (offline)*: load → clean → chunk → embed → store in a vector DB.
- *Query (online)*: (rewrite) → embed query → retrieve top-k → (rerank/grade) → build prompt → LLM → answer + citations.

**Chunking: why and how?**
- LLM context is limited and retrieval works better on focused passages; whole documents dilute the embedding.
- Too small loses context ("12 days" without saying *which* leave); too big makes retrieval imprecise and costs more tokens.
- **My approach**: first `MarkdownHeaderTextSplitter` (one chunk per policy section, so "Sick Leave" never mixes with
  "Maternity Leave"), then `RecursiveCharacterTextSplitter` (800 chars, 120 overlap; it tries paragraph → line →
  sentence → word boundaries). I **prepend the heading path** ("Leave Policy > 2. Sick Leave") to each chunk so
  it's self-describing. That's a simple form of *contextual chunking*.
- **Overlap** keeps facts that straddle a boundary retrievable from at least one chunk.
- Deterministic chunk IDs (SHA-1 of source + text) make re-ingestion idempotent.
- Alternatives: semantic chunking (split where embedding similarity drops), parent-document retrieval (retrieve small chunks, send the parent section), and late chunking.

**Embeddings**: a model maps text to a dense vector (384 numbers for bge-small) where semantic similarity ≈ cosine
similarity. "Time off when my father passed away" lands near "Bereavement Leave" with zero word overlap.
Query and documents must use the **same model**; if you change the model, you must re-embed everything.
I chose **bge-small via FastEmbed**: free, local, CPU-only ONNX (no PyTorch), good quality for its size, and
no data leaves the machine, which matters for HR data. Swappable with `EMBEDDING_PROVIDER=openai`.

**Cosine similarity**: cos θ = (a·b)/(|a||b|), comparing direction rather than magnitude. With normalised vectors it equals the dot product.
Chroma returns a *distance* (1 − cos); LangChain's `relevance_score` converts it back to similarity.

**Vector database / ANN**: brute force compares the query with every vector (O(n)). Vector DBs use **Approximate
Nearest Neighbour** indexes. Chroma uses **HNSW** (Hierarchical Navigable Small World): a multi-layer graph you
greedily walk from coarse to fine. That's roughly logarithmic search with ~95–99% recall. Others: IVF (clustering), PQ (compression).
Options: Chroma (local/dev), FAISS (library), pgvector (Postgres), Qdrant/Weaviate/Pinecone/Milvus, Azure AI Search.

**Hybrid search: why?** Dense retrieval understands meaning but can blur exact tokens such as acronyms (POSH, PF, LWP),
codes and numbers ("INR 15,000"). **BM25** is classic keyword ranking (TF-IDF family with term-frequency
saturation and document-length normalisation) and is exact about those. Combining them is the industry default.

**Reciprocal Rank Fusion**: `score(d) = Σ 1/(k + rank_i(d))`, k = 60. It uses only ranks, so I never need to
normalise cosine scores against BM25 scores (different scales). Documents ranked well by both rise to the top.
I over-fetch 3×k from each retriever, fuse, and keep the top k.

**Re-ranking** (an improvement to mention): a cross-encoder (e.g. `bge-reranker`, Cohere Rerank) reads query + chunk
*together*, which is more accurate than bi-encoder embeddings but slower, so you only apply it to the top 20–50 candidates.

**Query rewriting**: follow-ups like "Can I carry *it* forward?" are meaningless to a retriever. The `rewrite` node
uses chat history to produce a standalone query ("Can sick leave be carried forward?"). Other techniques: multi-query,
HyDE (embed a hypothetical answer), step-back prompting.

**Relevance grading / Corrective RAG**: my `grade` node runs a cheap check first (is the best cosine score ≥ threshold?)
and, only if that passes, ONE LLM call asks "does this context answer the question? yes/no". If no, we
**escalate** instead of answering. This is a simplified **CRAG / Self-RAG** pattern. I grade all chunks in one call
rather than per-chunk to save latency and cost.

**Hallucination control (list them):** grounded prompt ("answer ONLY from context, else say you don't know"),
low temperature (0.1), the relevance gate, citations, numbers from the DB instead of the LLM, escalation, and evaluation.

**Prompt injection**: a document (or user) could contain "ignore previous instructions…". Mitigations here:
context in a delimited, numbered block; the system prompt states that context is data, not instructions; the LLM has no
dangerous tools; and tickets are created by code, not by the LLM. In production, add input/output filters (e.g. Azure AI
Content Safety / Prompt Shields) and only ingest documents from trusted sources.

**Context window and "lost in the middle"**: LLMs attend best to the start and end of long prompts. Keep k small (4),
order by relevance, and keep chunks focused.

---

## 4. LangChain: what it does in this project

LangChain = a framework of **standard interfaces + integrations** for LLM apps. What I use:
- **Chat models** (`BaseChatModel`): `ChatGroq`, `ChatOpenAI`, `AzureChatOpenAI`, `ChatGoogleGenerativeAI`,
  `ChatOllama` all share `.invoke/.stream/.ainvoke`. My `get_llm()` factory lets me switch providers through config with
  zero code changes. I even wrote a custom `MockChatModel` by subclassing `BaseChatModel` (`_generate`, `_stream`).
- **Messages**: `SystemMessage`, `HumanMessage`, `AIMessage` to build prompts with history.
- **Document loaders** (`PyPDFLoader`) and the `Document` type (page_content + metadata).
- **Text splitters**: `MarkdownHeaderTextSplitter`, `RecursiveCharacterTextSplitter`.
- **Embeddings** interface (`FastEmbedEmbeddings`, `OpenAIEmbeddings`, and my own `HashingEmbeddings`).
- **Vector store** wrapper (`langchain_chroma.Chroma`: `from_documents`, `similarity_search_with_relevance_scores`).

**LCEL** (LangChain Expression Language): `prompt | llm | parser` composes Runnables with streaming/batch/async for free.
I don't need it inside LangGraph nodes, but know it: `chain = ChatPromptTemplate.from_messages([...]) | llm | StrOutputParser()`.

**Why not just call the OpenAI SDK directly?** You could. LangChain buys provider portability, ready-made loaders/
splitters/vector-store integrations, and callbacks/tracing (LangSmith). The cost is abstraction overhead and API churn.
For a small app either is fine; I value being able to switch to Azure OpenAI via one env var.

---

## 5. LangGraph: the agent (expect "why LangGraph?")

**What is it?** A library for building LLM apps as **graphs/state machines**: nodes are Python functions, edges
define the flow, and a typed **state** object is passed between nodes. It supports cycles, conditional branching,
streaming, persistence/checkpointing and human-in-the-loop.

**Core API (as used in `graph.py`)**
```python
g = StateGraph(HRState)                 # HRState is a TypedDict
g.add_node("route", route)              # node = fn(state) -> partial state update (a dict)
g.add_edge(START, "route")
g.add_conditional_edges("route", lambda s: s["route"], {...})  # router fn picks the next node
g.add_edge("generate", END)
graph = g.compile()                     # → a Runnable: invoke / stream / astream
```
- Nodes return **partial updates**; LangGraph merges them into the state (by default the key is overwritten; with a
  **reducer** like `Annotated[list, add_messages]` it's appended).
- `astream(stream_mode=["updates","messages"])`: "updates" emits after each node (I show progress in the UI);
  "messages" emits LLM tokens as they're generated (typing effect). I filter tokens by `metadata["langgraph_node"]`.

**Why LangGraph instead of a chain or a ReAct agent?**
- A **chain** is linear; I need branching (RAG vs DB tool vs escalation vs chitchat) and a conditional exit after grading.
- A fully autonomous **ReAct/tool-calling agent** lets the LLM decide everything. It is flexible but less predictable,
  slower (more LLM calls) and harder to test. HR answers must be reliable, so I used a **controlled workflow**: the LLM
  makes *bounded* decisions (classify, rewrite, grade, answer) while the control flow stays in code.
  This is the "workflow vs agent" trade-off; choose the least autonomy that solves the problem.
- Each node is a plain function, so it's **unit-testable** (`tests/test_graph.py`).

**Memory**: LangGraph offers checkpointers (`MemorySaver`, `SqliteSaver`, `PostgresSaver`) keyed by `thread_id`.
I store chat history in my own `chat_messages` table and load the last 6 messages per request, which keeps the API
**stateless** (any pod can serve any user in Kubernetes). The alternative is `PostgresSaver`, which also enables
resuming interrupted runs and human-in-the-loop `interrupt()`.

**How would you add human approval?** Use LangGraph `interrupt()` before `escalate` with a checkpointer, so the run pauses,
HR reviews, then `Command(resume=...)` continues.

**Multi-agent?** (Your Maximus work mentions multi-agent.) Patterns: a *supervisor* routes to specialist agents (policy
agent, payroll agent, IT agent), or a *hierarchical* setup. My `route` node is effectively a supervisor with specialist
sub-flows; each could become its own subgraph.

---

## 6. LLM and prompt-engineering questions

- **Which LLM and why?** Default Groq Llama-3.3-70B (fast, free tier) for development; Azure OpenAI GPT-4o-mini for an
  enterprise (data residency, SLAs, content filtering, private networking). The choice is config-only.
- **Temperature 0.1**: factual QA should be deterministic. Higher temperature means more creative and more risk.
- **Tokens and cost**: cost ≈ (prompt + completion tokens) × price. RAG prompt ≈ system (~150) + 4 chunks × ~200 +
  history + question ≈ 1–1.5k tokens. Reduce cost with fewer/smaller chunks, a cheaper model for routing/grading, caching, and skipping the grader when scores are very high.
- **Number of LLM calls per question**: route (1) + rewrite (1 if history) + grade (1) + generate (1), so 3–4.
  Optimisations: rule-based routing for obvious cases, a small/fast model for route/grade, merging route+rewrite into one structured-output call.
- **Prompt techniques used**: role + rules in the system prompt, delimited/numbered context, explicit refusal instruction,
  output-format instruction (citations, length), classification with a fixed label set + defensive parsing
  (fallback to `policy_question` if the LLM returns junk). For production, use `llm.with_structured_output(PydanticModel)`.
- **Streaming**: improves *perceived* latency; first token in ~300 ms instead of waiting 3 s for the full answer.

---

## 7. Backend / frontend / data questions

**FastAPI**: async Python web framework on Starlette + Pydantic. Pydantic models validate requests (`question` must
be 1–2000 chars → automatic 422), auto OpenAPI docs at `/docs`. The `lifespan` hook loads the index/LLM once at startup
(not per request).

**SSE vs WebSockets**: Server-Sent Events are one-way server→client over plain HTTP, simple, and proxy-friendly, which is perfect for
streaming tokens. WebSockets are bidirectional (needed for live collaboration or voice). My events: `step`, `token`, `final`.
The browser's `EventSource` only supports GET, so the React client parses the stream from `fetch()` with a `ReadableStream`.

**Health vs readiness endpoints**: `/health` = the process is alive; `/ready` = DB reachable and index loaded. These map to k8s probes.

**Why store history in the DB?** Statelessness: with 2+ replicas behind a load balancer, in-memory history would be lost
when a request hits another pod.

**Database design**: `employees` (mock HRMS: id, name, dept, leave balances, HRBP), `tickets` (FK → employees, status,
created_at), `chat_messages` (session_id indexed, role, content). SQLAlchemy 2.0 ORM, so the same code runs on SQLite
(dev/tests) and PostgreSQL (compose/k8s) by changing `DATABASE_URL`. In production add Alembic migrations.

**SQL vs NoSQL here**: tickets/employees are relational with FKs, so SQL fits. Chat logs could go to a document store
(Cosmos DB/Mongo) at scale. Vectors live in a vector store.

**Streamlit**: a Python-only UI; the script re-runs top-to-bottom on every interaction, and `st.session_state` persists
values across reruns. `st.chat_message`, `st.chat_input`, `st.status` show the agent steps. Great for internal tools and demos.
**React** version: hooks (`useState`, `useEffect`, `useRef`), immutable state updates for streaming tokens,
Vite dev proxy `/api → :8000` to avoid CORS. Why both: Streamlit for fast prototyping, React for a production UI.

**Security / enterprise questions**
- *AuthN/AuthZ*: the demo uses a dropdown as "SSO". In production: Azure AD / Entra ID (OIDC), the API validates the JWT, and
  `employee_id` comes from the token, **never from the request body** (otherwise anyone could read anyone's leave balance).
- *Document-level access control*: store `allowed_roles`/`country` in chunk metadata and **filter at retrieval time**
  (e.g. managers-only policies, India vs US policies).
- *PII*: don't log full prompts in production; mask PII; choose a provider with no-training/data-residency guarantees (Azure OpenAI).
- *Rate limiting*: at the ingress/API gateway, plus per-user quotas.

---

## 8. Evaluation (shows maturity; most candidates can't answer this)

`eval/golden_set.json`: 20 answerable questions with the expected source + expected fact, plus 2 unanswerable ones.
- **Retrieval**: hit@k (is the right doc in the top k?) and **MRR** (how high is it ranked?).
- **Generation**: answer accuracy (expected fact present), and **abstention accuracy** (does it refuse/escalate on out-of-scope?).
- Offline baseline (hashing embeddings + extractive mock, i.e. the weakest setup): hit@4 95%, MRR 0.80, answer accuracy 90%,
  abstention 50%. **Run it with bge-small + a real LLM and quote your own numbers.**
- More advanced: **RAGAS** metrics (faithfulness, answer relevancy, context precision/recall), LLM-as-judge, user
  thumbs up/down feedback, tracing with **LangSmith** / Langfuse.
- I use it as a **regression test**: if a chunking or prompt change lowers hit@k, I know before shipping. CI runs it.

---

## 9. Before the interview: do these yourself (≈ 1 hour)

1. `pip install -r requirements.txt`, get a free Groq key, `cp .env.example .env`, set `GROQ_API_KEY`.
2. `python -m app.ingest`, `uvicorn app.api:app --reload`, open `/docs`, and call `/chat` from Swagger.
3. `streamlit run ui/streamlit_app.py`. Ask: sick leave → "can I carry it forward?" → "what's my leave balance?" →
   "do we get stock options?" (watch it escalate) → switch employee → `/tickets`.
4. `pytest -q`, then `python -m eval.evaluate` and **note your numbers**.
5. Add your own PDF to `data/policies/`, re-ingest, and ask about it. (They may ask "how do you add a new document?")
6. `docker compose up --build`.
7. `./scripts/k8s-up.sh`, then `./scripts/k8s-demo.sh`. Practise narrating each step out loud.
8. Break things on purpose: wrong image tag (ImagePullBackOff), wrong `DATABASE_URL` in the ConfigMap (init container
   stuck), set the memory limit to 100Mi (OOMKilled). Debug each with `describe` / `logs`. This builds real confidence.

---

## 10. Likely questions: quick answers

1. **Walk me through what happens when a user asks a question.** UI → POST `/chat/stream` → load last 6 messages →
   graph: route → rewrite → hybrid retrieve → grade → generate (streamed) → save both messages → `final` event with sources.
2. **How do you prevent hallucinations?** See Section 3's list. Highlight the relevance gate + escalation + DB-sourced numbers.
3. **What if the answer spans two documents?** top-k from all docs; the LLM synthesises and cites both ([1], [2]). For multi-hop questions, use query decomposition.
4. **How do you update the knowledge base?** Drop files into `data/policies`, call `POST /ingest` (or run the ingestion
   Job/CronJob). Deterministic IDs make it idempotent. For large corpora, do incremental ingestion by file hash.
5. **Why Chroma?** Zero-ops, local, persistent, metadata filtering. In production on Azure: Azure AI Search (hybrid + semantic
   ranker built in) or pgvector to reuse Postgres.
6. **How do you choose chunk size / k?** Empirically with the eval set: try 400/800/1200 and k = 3/4/6, and compare hit@k, answer accuracy and token cost.
7. **What's the latency breakdown?** Embedding the query ~10 ms (local), retrieval ~5 ms, each LLM call 300 ms–2 s (dominant).
   Improve with streaming, a smaller model for route/grade, parallel calls, and caching.
8. **How would you handle PDFs with tables/scans?** Better parsers (Azure Document Intelligence, Unstructured,
   PyMuPDF), OCR for scans, tables converted to markdown, and per-page metadata for citations (the loader already stores the page).
9. **Multilingual employees (Kannada/Hindi)?** Use a multilingual embedding model (bge-m3, multilingual-e5) and let the LLM
   answer in the user's language. Policies can stay in English.
10. **What would you improve next?** A cross-encoder reranker, structured outputs for routing, the LangGraph PostgresSaver +
    `interrupt()` for HR approval, Entra ID auth + doc-level ACLs, LangSmith tracing, RAGAS in CI, and a semantic cache.
11. **Biggest challenge?** Good candidates: (a) follow-up questions retrieving the wrong policy → added the rewrite node;
    (b) confident answers to out-of-scope questions → added grading + escalation; (c) acronyms missed by embeddings →
    added BM25 hybrid search; (d) scaling with in-memory chat history → moved history to Postgres (stateless pods).
    Tell it as STAR: Situation, Task, Action, Result.
12. **How is this relevant to our enterprise work?** It's the same pattern for any internal knowledge source (IT
    helpdesk, sales playbooks, compliance): connectors → ingestion → hybrid retrieval → controlled agent → enterprise
    integrations (HRMS, ticketing like ServiceNow, which is on your resume) → deploy on AKS with Azure OpenAI.

### Connect it to your Maximus experience
- Multi-agent customer-service workflow (LLMs + RAG): "same retrieve → draft → review pattern; LangGraph would model the supervisor + specialists."
- Salesforce/AWS integrations: "the `leave_balance` and `escalate` nodes are exactly where I'd call real enterprise APIs: Workday/SAP for balances, ServiceNow/Salesforce for tickets, wrapped as tools."
- Serverless document generation (Lambda, S3): "contrast: Lambda is great for event-driven, short-lived jobs; Kubernetes for long-running services with steady traffic, streaming connections and more control."

---

## 11. Rapid-fire glossary

| Term | One-liner |
|---|---|
| Token | ~¾ of a word; the unit of LLM input/output and billing |
| Context window | Max tokens (prompt + output) a model can handle per call |
| Embedding | Dense vector capturing meaning; similar meaning → close vectors |
| Bi-encoder vs cross-encoder | Encode separately (fast, for retrieval) vs encode the pair jointly (accurate, for reranking) |
| HNSW | Graph-based approximate nearest-neighbour index used by most vector DBs |
| BM25 | Keyword ranking: term frequency (saturating) × inverse document frequency, length-normalised |
| RRF | Rank fusion: Σ 1/(60 + rank) |
| Top-k | Number of chunks passed to the LLM |
| Grounding | Constraining answers to provided sources |
| Agent | An LLM deciding actions/tools in a loop; *workflow* = predefined paths with LLM steps |
| Tool / function calling | The LLM outputs structured arguments for a function your code executes |
| Checkpointer | LangGraph persistence of state per thread, enabling memory, resume and human-in-the-loop |
| Temperature | Randomness of sampling; low = deterministic |
| Guardrails | Input/output checks: PII, toxicity, prompt injection, topic restriction |
| Semantic cache | Reuse answers for semantically similar past questions |
