import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Conversation, Message, SupportTicket, User
from app.db.session import get_db
from app.schemas import ConversationDetail, ConversationOut, MessageOut, ReplyIn
from app.services.tickets import escalate_conversation

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _get_conv(db: Session, user: User, conv_id: uuid.UUID) -> Conversation:
    conv = db.scalar(
        select(Conversation).where(Conversation.id == conv_id, Conversation.organization_id == user.organization_id)
    )
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    status: str | None = None, limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    stmt = select(Conversation).where(Conversation.organization_id == user.organization_id)
    if status:
        stmt = stmt.where(Conversation.status == status)
    convs = db.scalars(stmt.order_by(Conversation.last_message_at.desc()).limit(min(max(limit, 1), 200))).all()
    out = []
    for c in convs:
        first = db.scalar(
            select(Message.content)
            .where(Message.conversation_id == c.id, Message.role == "customer")
            .order_by(Message.created_at)
            .limit(1)
        )
        item = ConversationOut.model_validate(c)
        item.preview = (first or "")[:120]
        out.append(item)
    return out


@router.get("/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = _get_conv(db, user, conv_id)
    messages = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)).all()
    ticket_id = db.scalar(
        select(SupportTicket.id)
        .where(SupportTicket.conversation_id == conv.id, SupportTicket.organization_id == user.organization_id)
        .order_by(SupportTicket.created_at.desc())
        .limit(1)
    )
    detail = ConversationDetail.model_validate(conv, from_attributes=True)
    detail.messages = [MessageOut.model_validate(m) for m in messages]
    detail.ticket_id = ticket_id
    return detail


@router.post("/{conv_id}/reply", response_model=MessageOut, status_code=201)
def human_reply(conv_id: uuid.UUID, body: ReplyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = _get_conv(db, user, conv_id)
    if conv.status != "escalated":
        escalate_conversation(db, conv, f"{user.full_name} took over the conversation")  # AI goes silent
    msg = Message(
        conversation_id=conv.id, organization_id=user.organization_id, role="human_agent", content=body.content.strip()
    )
    db.add(msg)
    ticket = db.scalar(
        select(SupportTicket).where(
            SupportTicket.conversation_id == conv.id,
            SupportTicket.organization_id == user.organization_id,
            SupportTicket.status != "resolved",
        )
    )
    if ticket:
        if ticket.status == "open":
            ticket.status = "in_progress"
        if ticket.assigned_to is None:
            ticket.assigned_to = user.id
    db.commit()
    return msg
