import uuid
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    title: str
    page: int | None
    content: str
    score: float  # cosine similarity: 1.0 = identical direction

    def to_dict(self) -> dict:
        return asdict(self)


def search_chunks(db: Session, org_id: uuid.UUID, query_vector: list[float], k: int) -> list[RetrievedChunk]:
    """Top-k nearest chunks for ONE organization. The org filter is the tenant boundary."""
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.content,
            DocumentChunk.page_number,
            Document.title,
            distance.label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.organization_id == org_id, Document.status == "ready")
        .order_by(distance)
        .limit(k)
    )
    return [
        RetrievedChunk(str(r.id), str(r.document_id), r.title, r.page_number, r.content, 1.0 - float(r.distance))
        for r in db.execute(stmt)
    ]
