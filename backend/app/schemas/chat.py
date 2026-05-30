from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    document: str
    excerpt: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    conversation_id: str | None = None


class ChatDoneEvent(BaseModel):
    conversation_id: str
    message_id: str
    sources: list[SourceCitation]
