from typing import Literal

from pydantic import BaseModel, Field

'''planner output (agents.research_planner)'''
class ResearchStep(BaseModel):
    """A single step in a research plan."""

    step_id: int
    task_type: Literal[
        "market_analysis",
        "financial_analysis",
        "quantitative_analysis",
        "comparison",
        "mixed",
    ]
    tool_category: Literal[
        "market",
        "financial",
        "quantitative",
        "research",
    ]
    objective: str
    required: bool = True


class ResearchPlan(BaseModel):
    """Structured research plan generated from an analyzed query."""

    query: str
    steps: list[ResearchStep] = Field(default_factory=list)
    research_questions: list[str]

'''src.tools.(research tool) output (tools / Research MCP)'''
class ResearchSource(BaseModel):
    """A single external research source."""

    title: str
    url: str
    content: str


class ResearchResult(BaseModel):
    """Validated external research result."""

    query: str
    sources: list[ResearchSource] = Field(default_factory=list)