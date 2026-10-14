from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Conversation, Feedback, Message, SupportTicket, User
from app.db.session import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = user.organization_id

    def count(stmt) -> int:
        return db.scalar(stmt) or 0

    since = datetime.now(timezone.utc) - timedelta(days=13)
    day = func.date_trunc("day", Conversation.created_at)
    by_day = {
        r[0].date().isoformat(): r[1]
        for r in db.execute(
            select(day, func.count()).where(Conversation.organization_id == org, Conversation.created_at >= since).group_by(day)
        )
    }
    days = [(since + timedelta(days=i)).date().isoformat() for i in range(14)]
    ratings = dict(
        db.execute(select(Feedback.rating, func.count()).where(Feedback.organization_id == org).group_by(Feedback.rating)).all()
    )
    return {
        "total_conversations": count(select(func.count(Conversation.id)).where(Conversation.organization_id == org)),
        "total_messages": count(select(func.count(Message.id)).where(Message.organization_id == org)),
        "resolved_conversations": count(
            select(func.count(Conversation.id)).where(Conversation.organization_id == org, Conversation.status == "resolved")
        ),
        "escalated_conversations": count(
            select(func.count(func.distinct(SupportTicket.conversation_id))).where(SupportTicket.organization_id == org)
        ),
        "open_tickets": count(
            select(func.count(SupportTicket.id)).where(SupportTicket.organization_id == org, SupportTicket.status != "resolved")
        ),
        "unanswered_questions": count(
            select(func.count(Message.id)).where(
                Message.organization_id == org, Message.role == "customer", Message.is_unanswered
            )
        ),
        "feedback_positive": ratings.get("up", 0),
        "feedback_negative": ratings.get("down", 0),
        "conversations_by_day": [{"date": d, "count": by_day.get(d, 0)} for d in days],
    }


@router.get("/unanswered")
def unanswered(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Message.content, Message.conversation_id, Message.created_at)
        .where(Message.organization_id == user.organization_id, Message.role == "customer", Message.is_unanswered)
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    return [{"question": r[0], "conversation_id": str(r[1]), "created_at": r[2].isoformat()} for r in rows]
