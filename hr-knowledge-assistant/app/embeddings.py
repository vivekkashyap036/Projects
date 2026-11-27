"""Embedding model factory.

An embedding model maps text -> a dense vector so that texts with similar
*meaning* end up close together (cosine similarity). We embed every chunk once
at ingestion time and embed the user's query at question time.
"""
import hashlib
import math
import re

from langchain_core.embeddings import Embeddings

from app.config import Settings

_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbeddings(Embeddings):
    """Tiny, dependency-free embedder used for tests and offline demos.

    It hashes word unigrams + bigrams into a fixed-size vector (the "hashing
    trick") and L2-normalises it. It captures keyword overlap, not meaning, so
    it is NOT a substitute for a real model -- but it is deterministic and
    needs no download, which makes CI fast and reliable.
    """

    def __init__(self, dim: int = 512):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        words = _TOKEN.findall(text.lower())
        feats = words + [f"{a}_{b}" for a, b in zip(words, words[1:])]
        vec = [0.0] * self.dim
        for f in feats:
            h = int(hashlib.md5(f.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0 if (h >> 8) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embeddings(settings: Settings) -> Embeddings:
    provider = settings.embedding_provider
    if provider == "fastembed":
        from langchain_community.embeddings import FastEmbedEmbeddings

        # bge-small: 384-dim, ~130 MB ONNX model, runs on CPU, no API key.
        return FastEmbedEmbeddings(model_name=settings.embedding_model or "BAAI/bge-small-en-v1.5")
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model or "text-embedding-3-small")
    if provider == "hash":
        return HashingEmbeddings()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {provider}")
