from pydantic import BaseModel, Field

from app.schemas.chat import SourceCitation


class StructuredAnswerResponse(BaseModel):
    summary: str = Field(..., min_length=1)
    key_points: list[str] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    confidence: str = Field(..., pattern=r"^(high|medium|low)$")
