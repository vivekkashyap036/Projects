from app.ingest import chunk_documents, load_documents
from app.retriever import HybridRetriever


def test_chunks_carry_heading_and_source(settings):
    chunks = chunk_documents(load_documents(settings.docs_dir), settings)
    sick = [c for c in chunks if c.metadata.get("section") == "2. Sick Leave"]
    assert sick, "markdown sections should become their own chunks"
    assert sick[0].metadata["source"] == "leave_policy.md"
    assert sick[0].page_content.startswith("Leave Policy")  # heading path prepended
    assert all(len(c.page_content) <= settings.chunk_size + 200 for c in chunks)


def test_chunk_ids_are_deterministic(settings):
    a = chunk_documents(load_documents(settings.docs_dir), settings)
    b = chunk_documents(load_documents(settings.docs_dir), settings)
    assert [c.metadata["chunk_id"] for c in a] == [c.metadata["chunk_id"] for c in b]


def test_hybrid_retrieval_finds_right_document(settings):
    r = HybridRetriever(settings)
    top = r.retrieve("hotel limit per night in metro cities", k=3)
    assert top[0].doc.metadata["source"] == "expense_reimbursement_policy.md"


def test_bm25_catches_rare_acronym(settings):
    r = HybridRetriever(settings)
    top = r.retrieve("POSH", k=3)
    assert any("POSH" in c.doc.page_content for c in top)
