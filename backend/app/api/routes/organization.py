from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.core.security import hash_password
from app.db.models import Organization, User
from app.db.session import get_db
from app.schemas import OrgOut, OrgUpdate, TeamCreate, UserOut

router = APIRouter(tags=["organization"])


@router.get("/organization", response_model=OrgOut)
def get_org(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.get(Organization, user.organization_id)


@router.patch("/organization", response_model=OrgOut)
def update_org(body: OrgUpdate, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    org = db.get(Organization, user.organization_id)
    data = body.model_dump(exclude_unset=True)
    name = data.pop("name", None)
    if name:
        org.name = name.strip()
    org.settings = {**(org.settings or {}), **data}  # reassign so the JSONB change is detected
    db.commit()
    return org


@router.get("/team", response_model=list[UserOut])
def list_team(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.organization_id == user.organization_id).order_by(User.created_at)).all()


@router.post("/team", response_model=UserOut, status_code=201)
def add_agent(body: TeamCreate, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    agent = User(
        organization_id=user.organization_id,
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role="agent",
    )
    db.add(agent)
    db.commit()
    return agent
