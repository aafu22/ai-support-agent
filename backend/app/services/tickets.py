import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import prompts
from app.db.models import Conversation, Message, SupportTicket
from app.services.providers.llm import generate

log = logging.getLogger(__name__)


def summarize_conversation(db: Session, conversation: Conversation) -> str:
    msgs = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id, Message.role.in_(("customer", "assistant", "human_agent")))
        .order_by(Message.created_at.desc())
        .limit(20)
    ).all()[::-1]
    transcript = "\n".join(f"{m.role}: {m.content[:400]}" for m in msgs)[:6000]
    try:
        return generate(prompts.SUMMARY_SYSTEM, [{"role": "user", "content": transcript}], max_tokens=200)
    except Exception:  # summary is a nicety; never block escalation on it
        log.warning("Summary generation failed", exc_info=True)
        last_customer = next((m.content for m in reversed(msgs) if m.role == "customer"), "")
        return f"Latest customer message: {last_customer[:300]}"


def escalate_conversation(
    db: Session, conversation: Conversation, reason: str, email: str | None = None, priority: str = "medium"
) -> SupportTicket:
    """Idempotent: returns the existing unresolved ticket if there is one."""
    ticket = db.scalar(
        select(SupportTicket).where(
            SupportTicket.conversation_id == conversation.id,
            SupportTicket.organization_id == conversation.organization_id,
            SupportTicket.status != "resolved",
        )
    )
    if email:
        conversation.customer_email = email
    if ticket is None:
        summary = summarize_conversation(db, conversation)
        conversation.summary = summary
        ticket = SupportTicket(
            organization_id=conversation.organization_id,
            conversation_id=conversation.id,
            escalation_reason=reason[:200],
            summary=summary,
            customer_email=conversation.customer_email,
            priority=priority,
        )
        db.add(ticket)
    elif email:
        ticket.customer_email = email
    conversation.status = "escalated"
    db.commit()
    return ticket


def set_ticket_status(db: Session, ticket: SupportTicket, status: str) -> None:
    ticket.status = status
    ticket.resolved_at = datetime.now(timezone.utc) if status == "resolved" else None
    conversation = db.get(Conversation, ticket.conversation_id)
    if conversation and conversation.organization_id == ticket.organization_id:
        if status == "resolved":
            conversation.status = "resolved"
        elif conversation.status == "resolved":
            conversation.status = "escalated"
