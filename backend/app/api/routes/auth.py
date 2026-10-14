from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import COOKIE_NAME, get_current_user
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, generate_public_key, hash_password, verify_password
from app.db.models import Organization, User
from app.db.session import get_db
from app.schemas import LoginIn, MeOut, OrgOut, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
auth_limit = Depends(rate_limit("auth", settings.auth_rate_limit_per_minute))

DEFAULT_ORG_SETTINGS = {"bot_name": "Support Assistant", "greeting": "Hi! How can I help you today?", "support_email": None}


def _set_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user.id, user.organization_id, user.role),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )


def _me(db: Session, user: User) -> MeOut:
    return MeOut(user=UserOut.model_validate(user), organization=OrgOut.model_validate(db.get(Organization, user.organization_id)))


@router.post("/register", response_model=MeOut, status_code=201, dependencies=[auth_limit])
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    org = Organization(name=body.org_name.strip(), public_key=generate_public_key(), settings=dict(DEFAULT_ORG_SETTINGS))
    db.add(org)
    db.flush()
    user = User(
        organization_id=org.id,
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role="owner",
    )
    db.add(user)
    db.commit()
    _set_cookie(response, user)
    return _me(db, user)


@router.post("/login", response_model=MeOut, dependencies=[auth_limit])
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else None)
    if not user or not ok or not user.is_active:
        raise HTTPException(401, "Invalid email or password")  # same message for both cases
    _set_cookie(response, user)
    return _me(db, user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, user)
