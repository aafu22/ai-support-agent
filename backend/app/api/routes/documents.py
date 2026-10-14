import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.core.config import settings
from app.db.models import Document, User
from app.db.session import get_db
from app.schemas import DocumentOut, FaqIn
from app.services.ingestion.extractors import detect_type
from app.services.ingestion.pipeline import process_document, process_faq

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_doc(db: Session, user: User, doc_id: uuid.UUID) -> Document:
    doc = db.scalar(select(Document).where(Document.id == doc_id, Document.organization_id == user.organization_id))
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("", response_model=DocumentOut, status_code=202)
def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(require_owner),
    db: Session = Depends(get_db),
):
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # never read more than the limit + 1 byte
    if len(data) > limit:
        raise HTTPException(413, f"File too large (limit {settings.max_upload_mb} MB)")
    filename = os.path.basename(file.filename or "upload")  # strips any path components
    try:
        file_type = detect_type(filename, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    doc = Document(
        organization_id=user.organization_id,
        uploaded_by=user.id,
        title=filename[:300],
        source_type="file",
        file_type=file_type,
        file_size=len(data),
    )
    db.add(doc)
    db.commit()
    background.add_task(process_document, doc.id, file_type, data)
    return doc


@router.post("/faq", response_model=DocumentOut, status_code=202)
def add_faq(body: FaqIn, background: BackgroundTasks, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    items = [(i.question.strip(), i.answer.strip()) for i in body.items]
    doc = Document(
        organization_id=user.organization_id,
        uploaded_by=user.id,
        title=f"FAQ: {body.title.strip()}"[:300],
        source_type="faq",
        file_type="faq",
        file_size=sum(len(q) + len(a) for q, a in items),
    )
    db.add(doc)
    db.commit()
    background.add_task(process_faq, doc.id, items)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Document).where(Document.organization_id == user.organization_id).order_by(Document.created_at.desc())
    ).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_doc(db, user, doc_id)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: uuid.UUID, user: User = Depends(require_owner), db: Session = Depends(get_db)):
    db.delete(_get_doc(db, user, doc_id))  # chunks go with it (ON DELETE CASCADE)
    db.commit()
