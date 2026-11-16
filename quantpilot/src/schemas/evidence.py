from typing import Literal

from pydantic import BaseModel, Field

'''
class EvidenceProvenance(BaseModel):
    step_id: int | None = None
    task_type: str
    tool_category: str
'''


class Evidence(BaseModel):
    """A single piece of research evidence linked to a claim."""

    claim: str
    source_type: Literal[
        "market_data",
        "financial_data",
        "quantitative_analysis",
        "external_research",
    ]
    source: str
    task_type: str
    tool_category: str
    step_id: int | None = None
    #provenance: list[EvidenceProvenance] = Field(default_factory=list)
    evidence: str
    confidence: float
    status: Literal[
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "UNSUPPORTED",
        "CONFLICTING",
        "UNVERIFIED",
    ]


class EvidenceLedger(BaseModel):
    """Collection of evidence items supporting research claims."""

    items: list[Evidence] = Field(default_factory=list)
