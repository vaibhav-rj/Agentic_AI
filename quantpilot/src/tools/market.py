from datetime import date, datetime
from typing import cast

import yfinance as yf

from src.schemas.market import HistoricalPrices, PriceBar

'''
O = Open       opening price
H = High       highest price
L = Low        lowest price
C = Close      closing price
V = Volume     number of shares/units traded
'''



def get_historical_prices(
    ticker: str,
    start: date,
    end: date,
) -> HistoricalPrices:
    """
    Retrieve historical daily market prices for a ticker.

    Use this tool when historical OHLCV price data is required for
    market analysis, performance analysis, or quantitative calculations.

    Args:
        ticker: Stock ticker symbol, such as "AAPL"(for Apple Inc.) or "MSFT"(for Microsoft Corporation).
        start: Inclusive start date for the requested historical period(data for this date is included).
        end: Exclusive end date for the requested historical period(data for this date is not included).

    Returns:
        HistoricalPrices containing validated OHLCV observations.

    Raises:
        ValueError: If the ticker or date range is invalid, or no data
            is available for the requested period.

    Limitations:
        Data availability and accuracy depend on the upstream market-data
        provider. This tool retrieves historical data only and does not
        provide investment recommendations.
    """

    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError("Ticker must not be empty.")

    if start >= end:
        raise ValueError("start must be earlier than end.")

    #Download bulk historical data for given ticker for a specific date range from Yahoo Finance using below.
    data = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
    )


    if data is None or data.empty:
        raise ValueError(
            f"No historical price data found for ticker '{ticker}' "
            f"between {start} and {end}."
        )

    if hasattr(data.columns, "levels"):
        data.columns = data.columns.get_level_values(0)

    bars: list[PriceBar] = []

    for timestamp, row in data.iterrows():
        # Cast the timestamp to a datetime object to resolve the type checker error
        timestamp = cast(datetime, timestamp)

        bars.append(
            PriceBar(
                date=timestamp.date(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                adj_close=float(row["Adj Close"]),
                volume=int(row["Volume"]),
            )
        )

    return HistoricalPrices(
        ticker=ticker,
        start=start,
        end=end,
        bars=bars,
    )