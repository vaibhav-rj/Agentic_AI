from datetime import date

from src.tools import get_historical_prices


result = get_historical_prices(
    ticker="AAPL",
    start=date(2025, 1, 1),
    end=date(2025, 2, 1),
)

print(type(result))
print(result.ticker)
print(len(result.bars))
print(result.bars[0])