import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import SupportTicket, User
from app.db.session import get_db
from app.schemas import TicketOut, TicketUpdate
from app.services.tickets import set_ticket_status

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _get_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> SupportTicket:
    ticket = db.scalar(
        select(SupportTicket).where(SupportTicket.id == ticket_id, SupportTicket.organization_id == user.organization_id)
    )
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(status: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(SupportTicket).where(SupportTicket.organization_id == user.organization_id)
    if status:
        stmt = stmt.where(SupportTicket.status == status)
    return db.scalars(stmt.order_by(SupportTicket.created_at.desc()).limit(200)).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_ticket(db, user, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: uuid.UUID, body: TicketUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = _get_ticket(db, user, ticket_id)
    fields = body.model_fields_set
    if "assigned_to" in fields:
        if body.assigned_to is not None:
            assignee = db.scalar(
                select(User).where(User.id == body.assigned_to, User.organization_id == user.organization_id, User.is_active)
            )
            if assignee is None:
                raise HTTPException(400, "Assignee must be an active member of your organization")
        ticket.assigned_to = body.assigned_to
    if body.priority:
        ticket.priority = body.priority
    if body.status:
        set_ticket_status(db, ticket, body.status)
    db.commit()
    return ticket
