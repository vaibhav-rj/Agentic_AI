from pydantic import BaseModel

class ReturnResult(BaseModel):
    """Validated return calculation."""
    ticker: str
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    total_return: float

class ReturnPoint(BaseModel):
    """A single periodic return observation."""
    date: str
    return_value: float


class ReturnSeries(BaseModel):
    """Validated periodic returns for a ticker."""
    ticker: str
    returns: list[ReturnPoint]

class VolatilityResult(BaseModel):
    """Validated volatility calculation."""
    ticker: str
    observations: int
    annualized_volatility: float

class DrawdownResult(BaseModel):
    """Validated maximum drawdown calculation."""
    ticker: str
    max_drawdown: float