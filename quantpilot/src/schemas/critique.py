from pydantic import BaseModel, Field


class Critique(BaseModel):
    critique: str
    challenged_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)