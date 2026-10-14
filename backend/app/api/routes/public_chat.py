import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_org_by_public_key
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.db.models import Conversation, Feedback, Message
from app.db.session import get_db
from app.schemas import (
    ChatIn,
    ChatOut,
    EscalateIn,
    FeedbackIn,
    PublicConfigOut,
    PublicConversationOut,
    PublicMessageOut,
)
from app.services.chat import get_conversation, handle_customer_message
from app.services.tickets import escalate_conversation

router = APIRouter(prefix="/public", tags=["public chat"])
chat_limit = Depends(rate_limit("chat", settings.chat_rate_limit_per_minute))
read_limit = Depends(rate_limit("read", 120))


@router.get("/config", response_model=PublicConfigOut, dependencies=[read_limit])
def chat_config(public_key: str = Query(min_length=8, max_length=64), db: Session = Depends(get_db)):
    org = get_org_by_public_key(db, public_key)
    s = org.settings or {}
    return PublicConfigOut(
        organization_name=org.name,
        bot_name=s.get("bot_name", "Support Assistant"),
        greeting=s.get("greeting", "Hi! How can I help you today?"),
    )


@router.post("/chat", response_model=ChatOut, dependencies=[chat_limit])
def chat(body: ChatIn, db: Session = Depends(get_db)):
    org = get_org_by_public_key(db, body.public_key)
    text = body.message.strip()
    if not text:
        raise HTTPException(422, "Message cannot be empty")
    result = handle_customer_message(db, org, body.session_id, text, body.conversation_id)
    return ChatOut(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        reply=result.reply,
        sources=result.sources,
        status=result.status,
        ai_replied=result.ai_replied,
    )


@router.get("/conversations/{conversation_id}", response_model=PublicConversationOut, dependencies=[read_limit])
def get_my_conversation(
    conversation_id: uuid.UUID,
    public_key: str = Query(min_length=8, max_length=64),
    session_id: str = Query(min_length=16, max_length=100),
    db: Session = Depends(get_db),
):
    org = get_org_by_public_key(db, public_key)
    conv = get_conversation(db, org.id, conversation_id, session_id)
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conv.id, Message.role != "system")
        .order_by(Message.created_at)
    ).all()
    return PublicConversationOut(status=conv.status, messages=[PublicMessageOut.model_validate(m) for m in messages])


@router.post("/messages/{message_id}/feedback", status_code=204, dependencies=[chat_limit])
def message_feedback(message_id: uuid.UUID, body: FeedbackIn, db: Session = Depends(get_db)):
    org = get_org_by_public_key(db, body.public_key)
    msg = db.scalar(
        select(Message).where(Message.id == message_id, Message.organization_id == org.id, Message.role == "assistant")
    )
    if msg is None:
        raise HTTPException(404, "Message not found")
    get_conversation(db, org.id, msg.conversation_id, body.session_id)  # must be this customer's conversation
    existing = db.scalar(select(Feedback).where(Feedback.message_id == msg.id))
    if existing:
        existing.rating, existing.comment = body.rating, body.comment
    else:
        db.add(Feedback(message_id=msg.id, organization_id=org.id, rating=body.rating, comment=body.comment))
    db.commit()


@router.post("/escalate", dependencies=[chat_limit])
def escalate(body: EscalateIn, db: Session = Depends(get_db)):
    org = get_org_by_public_key(db, body.public_key)
    conv = get_conversation(db, org.id, body.conversation_id, body.session_id)
    was_escalated = conv.status == "escalated"
    escalate_conversation(db, conv, "Customer requested a human", email=body.email.lower() if body.email else None)
    if not was_escalated:
        db.add(
            Message(
                conversation_id=conv.id,
                organization_id=org.id,
                role="assistant",
                content="I've passed your conversation to our support team. A team member will reply here soon.",
                intent="escalate",
            )
        )
        db.commit()
    return {"status": conv.status}
