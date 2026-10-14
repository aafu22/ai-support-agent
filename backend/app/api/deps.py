import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import Organization, User
from app.db.session import get_db

COOKIE_NAME = "access_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(401, "Not authenticated")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Not authenticated")
    user = db.get(User, user_id)  # re-load every request so deactivation takes effect immediately
    if not user or not user.is_active:
        raise HTTPException(401, "Not authenticated")
    return user


def require_owner(user: User = Depends(get_current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(403, "Only the account owner can do this")
    return user


def get_org_by_public_key(db: Session, public_key: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.public_key == public_key))
    if org is None:
        raise HTTPException(404, "Support chat not found")
    return org
