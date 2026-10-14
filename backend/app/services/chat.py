"""Customer chat orchestration: persistence around the LangGraph agent."""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.graph import build_graph
from app.core.config import settings
from app.db.models import Conversation, Message, Organization
from app.services.providers.llm import model_name
from app.services.tickets import escalate_conversation

log = logging.getLogger(__name__)

ERROR_REPLY = (
    "Sorry, I'm having trouble right now. Please try again "
    "in a moment, or ask to speak with a human."
)

ESCALATED_NOTICE = (
    "Your conversation is with our support team. "
    "A team member will reply here soon."
)


def _small_talk_reply(text: str) -> str | None:
    """Reply to simple conversational messages without invoking RAG."""
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s']", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    replies = {
        # Greetings
        "hi": "Hi! 👋 How can I help you today?",
        "hello": "Hello! 👋 How can I help you today?",
        "hey": "Hey! How can I help you today?",
        "hi there": "Hi there! 👋 How can I help you today?",
        "hello there": "Hello! How can I help you today?",
        "good morning": "Good morning! How can I help you today?",
        "good afternoon": "Good afternoon! How can I help you today?",
        "good evening": "Good evening! How can I help you today?",

        # Thanks
        "thanks": "You're welcome! Happy to help.",
        "thank you": "You're welcome! Happy to help.",
        "thanks a lot": (
            "You're very welcome! Let me know if you need anything else."
        ),
        "thank you so much": "You're very welcome! 😊",
        "thanks so much": "You're very welcome! 😊",
        "thx": "You're welcome! Happy to help.",

        # Acknowledgements
        "okay": "Sounds good! Let me know if you need anything else.",
        "ok": "Sounds good! Let me know if you need anything else.",
        "okay thanks": (
            "You're welcome! Let me know if I can help with anything else."
        ),
        "ok thanks": (
            "You're welcome! Let me know if you need anything else."
        ),
        "got it": "Great! Is there anything else I can help you with?",
        "understood": (
            "Great! Feel free to ask if you need anything else."
        ),
        "alright": (
            "Alright! Let me know if you need any further help."
        ),
        "sure": "Sure! Let me know if you need anything else.",
        "cool": "Glad to hear it! Anything else I can help with?",
        "great": "Great! Let me know if you need anything else.",

        # Closing messages
        "no thanks": "You're welcome! Have a great day.",
        "no thank you": "You're welcome! Have a great day.",
        "thats all": "Glad I could help! Have a great day.",
        "that's all": "Glad I could help! Have a great day.",
        "bye": "Goodbye! Have a great day.",
        "goodbye": (
            "Goodbye! Feel free to come back if you need help."
        ),
        "see you": "See you next time! Have a great day.",
        "take care": "You too! Have a great day.",
    }

    return replies.get(normalized)


@dataclass
class ChatResult:
    conversation_id: uuid.UUID
    status: str
    reply: str
    message_id: uuid.UUID | None = None
    sources: list[dict] = field(default_factory=list)
    ai_replied: bool = True


def get_conversation(
    db: Session,
    org_id: uuid.UUID,
    conversation_id: uuid.UUID,
    session_id: str,
) -> Conversation:
    """Only allow access to conversations belonging to this org and session."""
    conv = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == org_id,
            Conversation.session_id == session_id,
        )
    )

    if conv is None:
        raise HTTPException(404, "Conversation not found")

    return conv


def _check_daily_quota(db: Session, org_id: uuid.UUID) -> None:
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    used = db.scalar(
        select(func.count(Message.id)).where(
            Message.organization_id == org_id,
            Message.role == "customer",
            Message.created_at >= since,
        )
    )

    if (used or 0) >= settings.org_daily_message_limit:
        raise HTTPException(
            429,
            "This support chat has reached its daily limit. "
            "Please try again tomorrow.",
        )


def handle_customer_message(
    db: Session,
    org: Organization,
    session_id: str,
    text: str,
    conversation_id: uuid.UUID | None,
) -> ChatResult:
    """Persist a customer message and generate the appropriate response."""
    _check_daily_quota(db, org.id)

    if conversation_id:
        conv = get_conversation(
            db, org.id, conversation_id, session_id
        )
    else:
        conv = Conversation(
            organization_id=org.id,
            session_id=session_id,
        )
        db.add(conv)
        db.flush()

    customer_msg = Message(
        conversation_id=conv.id,
        organization_id=org.id,
        role="customer",
        content=text,
    )
    db.add(customer_msg)
    conv.last_message_at = datetime.now(timezone.utc)

    if conv.status == "resolved":
        conv.status = "ai_active"

    db.commit()

    # Escalated conversations belong to human agents.
    if conv.status == "escalated":
        return ChatResult(
            conv.id,
            conv.status,
            ESCALATED_NOTICE,
            ai_replied=False,
        )

    # Handle simple conversation without invoking document retrieval.
    small_talk_reply = _small_talk_reply(text)

    if small_talk_reply is not None:
        customer_msg.intent = "small_talk"

        reply = Message(
            conversation_id=conv.id,
            organization_id=org.id,
            role="assistant",
            content=small_talk_reply,
            intent="small_talk",
            is_unanswered=False,
        )

        db.add(reply)
        db.commit()

        return ChatResult(
            conversation_id=conv.id,
            status=conv.status,
            reply=small_talk_reply,
            message_id=reply.id,
            sources=[],
        )

    # Load recent conversation history for the agent.
    prior = db.scalars(
        select(Message)
        .where(
            Message.conversation_id == conv.id,
            Message.id != customer_msg.id,
            Message.role.in_(
                ("customer", "assistant", "human_agent")
            ),
        )
        .order_by(Message.created_at.desc())
        .limit(settings.max_history_messages)
    ).all()[::-1]

    history = [
        {
            "role": (
                "user" if message.role == "customer"
                else "assistant"
            ),
            "content": message.content,
        }
        for message in prior
    ]

    last_ai = next(
        (
            message
            for message in reversed(prior)
            if message.role == "assistant"
        ),
        None,
    )

    state = {
        "question": text,
        "history": history,
        "bot_name": (org.settings or {}).get(
            "bot_name", "Support Assistant"
        ),
        "prev_unanswered": bool(
            last_ai and last_ai.is_unanswered
        ),
    }

    try:
        final = build_graph(db, org.id).invoke(state)
    except Exception:
        log.exception(
            "Agent failed for conversation %s", conv.id
        )
        db.rollback()  # a failed DB statement would otherwise poison this session

        reply = Message(
            conversation_id=conv.id,
            organization_id=org.id,
            role="assistant",
            content=ERROR_REPLY,
            intent="error",
        )

        db.add(reply)
        db.commit()

        return ChatResult(
            conv.id,
            conv.status,
            ERROR_REPLY,
            reply.id,
        )

    outcome = final["outcome"]

    unanswered = (
        outcome in ("no_answer", "escalate")
        and final.get("intent", "knowledge_question")
        == "knowledge_question"
    )

    if unanswered:
        customer_msg.is_unanswered = True

    customer_msg.intent = final.get("intent")

    top = final.get("top_score")

    reply = Message(
        conversation_id=conv.id,
        organization_id=org.id,
        role="assistant",
        content=final["reply"],
        sources=final["sources"] or None,
        intent=outcome,
        confidence=round(top, 3) if top is not None else None,
        is_unanswered=unanswered,
        model_name=model_name(),
    )

    db.add(reply)
    db.commit()

    if outcome == "escalate":
        try:
            escalate_conversation(
                db,
                conv,
                final.get("reason") or "Escalated by AI",
            )
        except Exception:
            # The reply is already saved; never turn it into a 500.
            db.rollback()
            log.exception(
                "Escalation failed for conversation %s", conv.id
            )

    return ChatResult(
        conv.id,
        conv.status,
        final["reply"],
        reply.id,
        final["sources"],
    )