"""Ingestion pipeline:  load -> clean -> chunk -> embed -> store.

Run it with:  python -m app.ingest
In Kubernetes it runs as an initContainer before the API starts.
"""
import hashlib
import logging
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config import Settings, get_settings
from app.embeddings import get_embeddings

log = logging.getLogger(__name__)


def load_documents(docs_dir: str) -> list[Document]:
    """Load .md / .txt / .pdf files. Each Document keeps `source` metadata for citations."""
    docs: list[Document] = []
    for path in sorted(Path(docs_dir).rglob("*")):
        if path.suffix.lower() in {".md", ".txt"}:
            docs.append(Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name}))
        elif path.suffix.lower() == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader

            for page in PyPDFLoader(str(path)).load():
                page.metadata = {"source": path.name, "page": page.metadata.get("page", 0) + 1}
                docs.append(page)
    return docs


def chunk_documents(docs: list[Document], settings: Settings) -> list[Document]:
    """Two-stage chunking.

    1. Markdown files are first split on headings, so a chunk never mixes
       "Sick Leave" with "Maternity Leave". The heading path is stored in
       metadata AND prepended to the text, so the chunk is self-describing.
    2. Any section still longer than CHUNK_SIZE is split recursively
       (paragraph -> line -> sentence -> word) with CHUNK_OVERLAP characters
       of overlap so facts on a boundary are not lost.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "title"), ("##", "section")], strip_headers=True
    )
    recursive = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[Document] = []
    for doc in docs:
        if doc.metadata["source"].endswith(".md"):
            sections = header_splitter.split_text(doc.page_content)
        else:
            sections = [doc]
        for sec in sections:
            meta = {**doc.metadata, **sec.metadata}
            heading = " > ".join(v for k, v in meta.items() if k in ("title", "section"))
            for piece in recursive.split_text(sec.page_content):
                text = f"{heading}\n{piece}" if heading else piece
                chunk_id = hashlib.sha1(f"{meta['source']}|{text}".encode()).hexdigest()[:16]
                chunks.append(Document(page_content=text, metadata={**meta, "chunk_id": chunk_id}))
    return chunks


def build_index(settings: Settings | None = None, reset: bool = True) -> int:
    settings = settings or get_settings()
    docs = load_documents(settings.docs_dir)
    if not docs:
        raise RuntimeError(f"No documents found in {settings.docs_dir}")
    chunks = chunk_documents(docs, settings)
    if reset and Path(settings.chroma_dir).exists():
        shutil.rmtree(settings.chroma_dir)
    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(settings),
        ids=[c.metadata["chunk_id"] for c in chunks],  # deterministic ids => re-ingest is idempotent
        collection_name=settings.collection_name,
        persist_directory=settings.chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
    log.info("Indexed %d chunks from %d documents", len(chunks), len(docs))
    return len(chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = build_index()
    print(f"Indexed {n} chunks into {get_settings().chroma_dir}")
