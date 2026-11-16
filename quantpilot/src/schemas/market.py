from datetime import date

from pydantic import BaseModel, Field


class PriceBar(BaseModel):
    """A single historical OHLCV price observation."""

    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int = Field(ge=0)


class HistoricalPrices(BaseModel):
    """Validated historical price data for a ticker."""

    ticker: str
    start: date
    end: date
    bars: list[PriceBar]