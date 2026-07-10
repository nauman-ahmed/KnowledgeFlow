from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    type: str = Field(description="Ontology class local name, e.g. Concept, Author")
    name: str = Field(description="Human-readable label for the entity")
    uri: str | None = Field(default=None, description="Optional stable URI or slug")


class ExtractedRelation(BaseModel):
    predicate: str = Field(description="Ontology object-property local name, e.g. mentions")
    source_type: str
    source_name: str
    target_type: str
    target_name: str


class ExtractedCitation(BaseModel):
    text: str = Field(description="Citation string as it appears in the source text")
    context: str | None = Field(default=None, description="Surrounding sentence or clause")


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    citations: list[ExtractedCitation] = Field(default_factory=list)
