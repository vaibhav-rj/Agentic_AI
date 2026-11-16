from src.tools.financials import get_financial_metrics
from src.tools.market import get_historical_prices
from src.tools.quant import (
    calculate_total_return,
    calculate_return_series,
    calculate_volatility,
    calculate_max_drawdown,
)

TOOLS = [
    get_historical_prices,
    get_financial_metrics,
    calculate_total_return,
    calculate_return_series,
    calculate_volatility,
    calculate_max_drawdown,
]