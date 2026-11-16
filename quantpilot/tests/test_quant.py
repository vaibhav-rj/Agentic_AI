from datetime import date

from src.schemas.market import HistoricalPrices, PriceBar
from src.tools.quant import calculate_total_return, calculate_return_series, calculate_volatility, calculate_max_drawdown


def main():
    prices = HistoricalPrices(
        ticker="AAPL",
        start=date(2025, 1, 2),
        end=date(2025, 1, 3),
        bars=[
            PriceBar(
                date=date(2025, 1, 2),
                open=100,
                high=105,
                low=99,
                close=104,
                adj_close=100,
                volume=1000,
            ),
            PriceBar(
                date=date(2025, 1, 3),
                open=110,
                high=115,
                low=108,
                close=112,
                adj_close=110,
                volume=1200,
            ),
            PriceBar(
                date=date(2025, 1, 4),
                open=115,
                high=120,
                low=114,
                close=118,
                adj_close=115,
                volume=1300,
            ),
        ],
    )

    result = calculate_total_return(prices)
    series = calculate_return_series(prices)
    volatility = calculate_volatility(series)
    drawdown = calculate_max_drawdown(prices)

    print(type(result))
    print(result)
    print('-'*80)
    print(type(series))
    print(series)
    print('-'*80)
    print(type(volatility))
    print(volatility)
    print('-'*80)
    print(type(drawdown))
    print(drawdown)




if __name__ == "__main__":
    main()