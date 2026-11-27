"""Hybrid retriever: dense (semantic) search + sparse (BM25 keyword) search,
merged with Reciprocal Rank Fusion (RRF).

Why hybrid?
  * Dense vectors understand meaning: "time off when my father died" matches
    the "Bereavement Leave" section even with no shared words.
  * BM25 is exact about rare tokens: "POSH", "PF", "LWP", "INR 15,000" -- terms
    an embedding model may blur.
RRF combines the two ranked lists using only ranks (score = sum 1/(k + rank)),
so we never have to normalise cosine scores against BM25 scores.
"""
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.config import Settings
from app.embeddings import get_embeddings
from app.llm import keywords

RRF_K = 60  # standard constant from the original RRF paper (Cormack et al., 2009)


def _tokens(text: str) -> list[str]:
    return sorted(keywords(text)) or ["_"]


@dataclass
class RetrievedChunk:
    doc: Document
    vector_score: float  # cosine similarity in [0, 1]; 0 if found only by BM25
    rrf_score: float


class HybridRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = Chroma(
            collection_name=settings.collection_name,
            embedding_function=get_embeddings(settings),
            persist_directory=settings.chroma_dir,
            collection_metadata={"hnsw:space": "cosine"},
        )
        raw = self.store.get(include=["documents", "metadatas"])
        self.corpus = [Document(page_content=t, metadata=m) for t, m in zip(raw["documents"], raw["metadatas"])]
        self.bm25 = BM25Okapi([_tokens(d.page_content) for d in self.corpus]) if self.corpus else None

    @property
    def size(self) -> int:
        return len(self.corpus)

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        k = k or self.settings.top_k
        if not self.corpus:
            return []
        fetch = k * 3  # over-fetch from each retriever, then fuse and cut to k

        dense = self.store.similarity_search_with_relevance_scores(query, k=fetch)
        q_tokens = _tokens(query)
        bm25_scores = self.bm25.get_scores(q_tokens)
        sparse_idx = [i for i in sorted(range(len(self.corpus)), key=lambda i: -bm25_scores[i]) if bm25_scores[i] > 0][:fetch]

        fused: dict[str, RetrievedChunk] = {}
        for rank, (doc, score) in enumerate(dense):
            cid = doc.metadata["chunk_id"]
            fused[cid] = RetrievedChunk(doc, max(0.0, score), 1 / (RRF_K + rank + 1))
        for rank, i in enumerate(sparse_idx):
            doc = self.corpus[i]
            cid = doc.metadata["chunk_id"]
            item = fused.setdefault(cid, RetrievedChunk(doc, 0.0, 0.0))
            item.rrf_score += 1 / (RRF_K + rank + 1)

        return sorted(fused.values(), key=lambda c: -c.rrf_score)[:k]
