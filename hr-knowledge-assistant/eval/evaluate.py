"""Offline evaluation of retrieval and answers against a small golden set.

Metrics
  hit@k          : % of answerable questions whose expected source doc is in the top-k chunks
  MRR            : mean reciprocal rank of the first chunk from the expected source
  answer_acc     : % of answerable questions whose answer contains the expected fact
  abstain_acc    : % of UNanswerable questions where the bot correctly escalated instead of guessing

Usage:  python -m eval.evaluate            (uses your .env: real embeddings / LLM)
        EMBEDDING_PROVIDER=hash LLM_PROVIDER=mock python -m eval.evaluate   (offline)
"""
import json
import time
from pathlib import Path

from app import db
from app.config import get_settings
from app.graph import build_graph
from app.llm import get_llm
from app.retriever import HybridRetriever


def main() -> None:
    settings = get_settings()
    db.init_db()
    retriever = HybridRetriever(settings)
    graph = build_graph(settings, get_llm(settings), retriever)
    golden = json.loads((Path(__file__).parent / "golden_set.json").read_text())

    hits = rr = correct = answerable = abstain_ok = unanswerable = 0
    t0 = time.perf_counter()
    for item in golden:
        out = graph.invoke({"question": item["q"], "employee_id": "E1001", "history": []})
        if item["source"] is None:
            unanswerable += 1
            ok = not out.get("context_ok", True)
            abstain_ok += ok
            print(f"{'OK ' if ok else 'BAD'} [abstain] {item['q']}")
            continue
        answerable += 1
        sources = [r.doc.metadata["source"] for r in retriever.retrieve(item["q"])]
        if item["source"] in sources:
            hits += 1
            rr += 1 / (sources.index(item["source"]) + 1)
        ok = item["fact"].lower() in out["answer"].lower()
        correct += ok
        print(f"{'OK ' if ok else 'BAD'} {item['q']}\n     -> {out['answer'][:140]}")

    n = len(golden)
    print("\n=== Results ===")
    print(f"embeddings={settings.embedding_provider}  llm={settings.resolved_llm_provider()}  k={settings.top_k}")
    print(f"hit@{settings.top_k}:      {hits / answerable:.0%}")
    print(f"MRR:        {rr / answerable:.2f}")
    print(f"answer_acc: {correct / answerable:.0%}")
    print(f"abstain_acc:{abstain_ok / unanswerable:.0%}")
    print(f"avg latency per question: {(time.perf_counter() - t0) / n * 1000:.0f} ms")


if __name__ == "__main__":
    main()
