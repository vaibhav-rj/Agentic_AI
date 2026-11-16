from pydantic import BaseModel, Field


class FinalReport(BaseModel):
    user_query: str
    summary: str
    thesis: str
    conclusion: str
    confidence: float = Field(ge=0.0, le=1.0)
    normalized_results: list[dict]
    limitations: list[str]
    validation_remarks: str = Field(default="UNVERIFIED: Contextual review not yet completed.")