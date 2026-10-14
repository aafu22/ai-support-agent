"""Background ingestion: extract -> clean -> chunk -> embed -> store."""
import logging
import uuid

from app.core.config import settings
from app.db.models import Document, DocumentChunk
from app.db.session import SessionLocal
from app.services.ingestion.chunker import Chunk, chunk_pages
from app.services.ingestion.cleaner import clean_pages
from app.services.ingestion.extractors import extract
from app.services.providers.embeddings import embed_texts

log = logging.getLogger(__name__)


def _store(document_id: uuid.UUID, chunks: list[Chunk]) -> None:
    if not chunks:
        raise ValueError("No extractable text found (scanned PDFs need OCR, which is not supported).")
    vectors = embed_texts([c.text for c in chunks])
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if doc is None:  # deleted while processing
            return
        db.add_all(
            DocumentChunk(
                document_id=doc.id,
                organization_id=doc.organization_id,
                chunk_index=i,
                content=c.text,
                page_number=c.page,
                embedding=v,
            )
            for i, (c, v) in enumerate(zip(chunks, vectors))
        )
        doc.status, doc.chunk_count, doc.error_message = "ready", len(chunks), None
        db.commit()


def _fail(document_id: uuid.UUID, message: str) -> None:
    with SessionLocal() as db:
        doc = db.get(Document, document_id)
        if doc:
            doc.status, doc.error_message = "failed", message[:300]
            db.commit()


def process_document(document_id: uuid.UUID, file_type: str, data: bytes) -> None:
    try:
        pages = clean_pages(extract(file_type, data))
        _store(document_id, chunk_pages(pages, settings.chunk_size, settings.chunk_overlap))
    except ValueError as exc:  # user-facing problems (bad file, no text)
        _fail(document_id, str(exc))
    except Exception:
        log.exception("Ingestion failed for document %s", document_id)
        _fail(document_id, "Processing failed. Please try again or contact support.")


def process_faq(document_id: uuid.UUID, items: list[tuple[str, str]]) -> None:
    """One chunk per Q&A pair keeps each answer intact."""
    try:
        _store(document_id, [Chunk(None, f"Q: {q}\nA: {a}") for q, a in items])
    except Exception:
        log.exception("FAQ ingestion failed for document %s", document_id)
        _fail(document_id, "Processing failed. Please try again.")
