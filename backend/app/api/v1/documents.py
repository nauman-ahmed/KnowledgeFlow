from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Document
from app.schemas.documents import DocumentDetail, DocumentListResponse, DocumentSummary

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    stmt = select(Document).order_by(Document.updated_at.desc())
    documents = list(db.scalars(stmt).all())
    return DocumentListResponse(
        documents=[DocumentSummary.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get("/stats/summary")
def document_stats(db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.count()).select_from(Document)) or 0
    ready = db.scalar(
        select(func.count()).select_from(Document).where(Document.status == "ready")
    ) or 0
    chunks = db.scalar(select(func.coalesce(func.sum(Document.chunk_count), 0))) or 0
    return {"documents_total": total, "documents_ready": ready, "chunks_total": int(chunks)}


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentDetail:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail.model_validate(doc)
