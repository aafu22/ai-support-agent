"""initial schema

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768  # must match EMBEDDING_DIM in settings


def _created(name: str = "created_at", clock: bool = False) -> sa.Column:
    default = sa.text("clock_timestamp()") if clock else sa.func.now()
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=False)


def _org_fk() -> sa.Column:
    return sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("public_key", sa.String(64), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        _created(),
    )
    op.create_index("ix_organizations_public_key", "organizations", ["public_key"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _org_fk(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _created(),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _org_fk(),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        _created(),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        _org_fk(),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        _created(),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_organization_id", "document_chunks", ["organization_id"])
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _org_fk(),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("customer_email", sa.String(320), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        _created("last_message_at"),
        _created(),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        _org_fk(),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        sa.Column("intent", sa.String(40), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_unanswered", sa.Boolean(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        _created(clock=True),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_organization_id", "messages", ["organization_id"])

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _org_fk(),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("escalation_reason", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("customer_email", sa.String(320), nullable=True),
        sa.Column("assigned_to", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        _created(),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_support_tickets_organization_id", "support_tickets", ["organization_id"])
    op.create_index("ix_support_tickets_conversation_id", "support_tickets", ["conversation_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("message_id", sa.Uuid(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        _org_fk(),
        sa.Column("rating", sa.String(10), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        _created(),
    )
    op.create_index("ix_feedback_message_id", "feedback", ["message_id"], unique=True)
    op.create_index("ix_feedback_organization_id", "feedback", ["organization_id"])


def downgrade() -> None:
    for table in ("feedback", "support_tickets", "messages", "conversations", "document_chunks", "documents", "users", "organizations"):
        op.drop_table(table)
