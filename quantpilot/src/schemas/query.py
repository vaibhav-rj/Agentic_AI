from typing import Literal

from pydantic import BaseModel, Field


class ResearchQuery(BaseModel):
    """Structured representation of a validated research query."""

    original_query: str
    task_types: list[
        Literal[
            "market_analysis",
            "financial_analysis",
            "quantitative_analysis",
            "comparison",
            "mixed",
        ]
    ] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    research_questions: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    time_horizon: str | None = None