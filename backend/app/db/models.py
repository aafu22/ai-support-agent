"""All tables. Every tenant-owned table carries organization_id."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings as app_settings
from app.db.base import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _org_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    public_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = _created()


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = _org_fk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # owner | agent
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _created()


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = _org_fk()
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(20))  # file | faq
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing | ready | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _created()


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = _org_fk()
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding = mapped_column(Vector(app_settings.embedding_dim))
    created_at: Mapped[datetime] = _created()

    __table_args__ = (
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = _org_fk()
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ai_active")  # ai_active | escalated | resolved
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = _created()


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = _pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = _org_fk()
    role: Mapped[str] = mapped_column(String(20))  # customer | assistant | human_agent | system
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_unanswered: Mapped[bool] = mapped_column(Boolean, default=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # clock_timestamp() (not now()) so messages in one transaction still sort correctly
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[uuid.UUID] = _pk()
    organization_id: Mapped[uuid.UUID] = _org_fk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | in_progress | resolved
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low | medium | high
    escalation_reason: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = _created()
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[uuid.UUID] = _pk()
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), unique=True, index=True)
    organization_id: Mapped[uuid.UUID] = _org_fk()
    rating: Mapped[str] = mapped_column(String(10))  # up | down
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _created()
