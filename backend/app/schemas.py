import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / org ----------
class RegisterIn(BaseModel):
    org_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool = True


class OrgOut(ORM):
    id: uuid.UUID
    name: str
    public_key: str
    settings: dict


class MeOut(BaseModel):
    user: UserOut
    organization: OrgOut


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    bot_name: str | None = Field(default=None, min_length=1, max_length=60)
    greeting: str | None = Field(default=None, min_length=1, max_length=300)
    support_email: EmailStr | None = None


class TeamCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


# ---------- documents ----------
class DocumentOut(ORM):
    id: uuid.UUID
    title: str
    source_type: str
    file_type: str | None
    file_size: int
    status: str
    error_message: str | None
    chunk_count: int
    created_at: datetime


class FaqItem(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)


class FaqIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    items: list[FaqItem] = Field(min_length=1, max_length=100)


# ---------- public chat ----------
class PublicBase(BaseModel):
    public_key: str = Field(min_length=8, max_length=64)
    session_id: str = Field(min_length=16, max_length=100)


class ChatIn(PublicBase):
    message: str = Field(min_length=1, max_length=settings.max_message_chars)
    conversation_id: uuid.UUID | None = None


class SourceOut(BaseModel):
    id: int
    document_id: str
    title: str
    page: int | None = None
    snippet: str = ""


class ChatOut(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID | None
    reply: str
    sources: list[SourceOut]
    status: str
    ai_replied: bool


class PublicMessageOut(ORM):
    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceOut] | None = None
    created_at: datetime


class PublicConversationOut(BaseModel):
    status: str
    messages: list[PublicMessageOut]


class PublicConfigOut(BaseModel):
    organization_name: str
    bot_name: str
    greeting: str


class FeedbackIn(PublicBase):
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=1000)


class EscalateIn(PublicBase):
    conversation_id: uuid.UUID
    email: EmailStr | None = None


# ---------- admin conversations / tickets ----------
class MessageOut(ORM):
    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceOut] | None = None
    intent: str | None
    confidence: float | None
    is_unanswered: bool
    created_at: datetime


class ConversationOut(ORM):
    id: uuid.UUID
    status: str
    customer_name: str | None
    customer_email: str | None
    summary: str | None
    last_message_at: datetime
    created_at: datetime
    preview: str | None = None


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []
    ticket_id: uuid.UUID | None = None


class ReplyIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class TicketOut(ORM):
    id: uuid.UUID
    conversation_id: uuid.UUID
    status: str
    priority: str
    escalation_reason: str
    summary: str | None
    customer_email: str | None
    assigned_to: uuid.UUID | None
    created_at: datetime
    resolved_at: datetime | None


class TicketUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    assigned_to: uuid.UUID | None = None  # send null to unassign
