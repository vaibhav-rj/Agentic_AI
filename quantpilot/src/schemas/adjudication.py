from pydantic import BaseModel, Field
from typing import Literal


class Adjudication(BaseModel):
    decision: str = Field(pattern="^(PASS|FAIL)$")
    rationale: str
    evidence_debt: list[str] = Field(default_factory=list)
    missing_tools: list[
        Literal["market", "financial", "quantitative", "research"]
    ] = Field(default_factory=list)

    confidence: float = Field(ge=0.0, le=1.0)

    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_band: Literal[
        "FULLY_PASSED",
        "STRONGLY_PASSED",
        "FAIRLY_PASSED",
        "AVERAGE",
        "POOR",
        "FAILED",
    ] = "FAILED"