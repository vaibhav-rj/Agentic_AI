from pydantic import BaseModel


class FinancialMetric(BaseModel):
    """A single financial metric for a ticker."""
    name: str
    value: float | int | str | bool | None
    period: str | None = None


class FinancialMetrics(BaseModel):
    """Validated financial metrics for a ticker."""
    ticker: str
    metrics: list[FinancialMetric]