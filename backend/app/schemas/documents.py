from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    filename: str
    mime_type: str
    status: str
    chunk_count: int
    content_hash: str
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    storage_path: str
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]
    total: int
