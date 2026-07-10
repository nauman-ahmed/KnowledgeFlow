from pydantic import BaseModel, Field

from app.schemas.chat import SourceCitation


class GraphContext(BaseModel):
    retrieval_mode: str | None = None
    related_concepts: list[str] = Field(default_factory=list)
    graph_paths: list[str] = Field(default_factory=list)
    cypher_query: str | None = None
    cypher_error: str | None = None
    graph_results_count: int = 0


class StructuredAnswerResponse(BaseModel):
    summary: str = Field(..., min_length=1)
    key_points: list[str] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    confidence: str = Field(..., pattern=r"^(high|medium|low)$")
    graph_context: GraphContext | None = None
