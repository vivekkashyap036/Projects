"""Tests run fully offline: hashing embeddings + mock LLM + throwaway SQLite/Chroma."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="hr-tests-")
os.environ.update(
    {
        "EMBEDDING_PROVIDER": "hash",
        "LLM_PROVIDER": "mock",
        "RELEVANCE_THRESHOLD": "0.1",
        "CHROMA_DIR": f"{_tmp}/chroma",
        "DATABASE_URL": f"sqlite:///{_tmp}/hr.db",
        "DOCS_DIR": os.path.join(os.path.dirname(__file__), "..", "data", "policies"),
    }
)

import pytest  # noqa: E402

from app import db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.ingest import build_index  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session", autouse=True)
def _index(settings):
    db.init_db()
    build_index(settings)


@pytest.fixture(scope="session")
def graph(settings):
    from app.graph import build_graph
    from app.llm import get_llm
    from app.retriever import HybridRetriever

    return build_graph(settings, get_llm(settings), HybridRetriever(settings))
