from pydantic import BaseModel, Field


class DocumentSearchHit(BaseModel):
    id: str
    title: str
    filename: str
    snippet: str
    score: float = 1.0


class ConversationSearchHit(BaseModel):
    id: str
    title: str
    snippet: str
    updated_at: str


class SearchResponse(BaseModel):
    query: str
    documents: list[DocumentSearchHit] = Field(default_factory=list)
    conversations: list[ConversationSearchHit] = Field(default_factory=list)
