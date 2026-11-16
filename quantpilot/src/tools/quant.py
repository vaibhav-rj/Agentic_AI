from src.schemas.market import HistoricalPrices
from src.schemas.quant import ReturnResult, ReturnPoint, ReturnSeries, VolatilityResult, DrawdownResult

import math

def calculate_total_return(
    prices: HistoricalPrices,
) -> ReturnResult:
    """
    Calculate total price return from historical price data.

    Use this tool when performance or return analysis is required.

    Args:
        prices: Validated historical price observations.

    Returns:
        ReturnResult containing the start/end prices and total return.

    Raises:
        ValueError: If fewer than two price observations exist.
    """

    if len(prices.bars) < 2:
        raise ValueError("At least two price observations are required.")

    first = prices.bars[0]
    last = prices.bars[-1]

    total_return = (last.adj_close / first.adj_close) - 1

    return ReturnResult(
        ticker=prices.ticker,
        start_date=str(first.date),
        end_date=str(last.date),
        start_price=first.adj_close,
        end_price=last.adj_close,
        total_return=total_return,
    )

def calculate_return_series(
    prices: HistoricalPrices,
) -> ReturnSeries:
    """
    Calculate periodic returns from historical adjusted prices.

    Use this tool when volatility, drawdown, or other statistical
    analysis requires a series of returns.

    Args:
        prices: Validated historical price observations.

    Returns:
        ReturnSeries containing period-by-period returns.
    """

    if len(prices.bars) < 2:
        raise ValueError("At least two price observations are required.")

    returns = [
        ReturnPoint(
            date=str(prices.bars[i].date),
            return_value=(
                prices.bars[i].adj_close
                / prices.bars[i - 1].adj_close
            ) - 1,
        )
        for i in range(1, len(prices.bars))
    ]

    return ReturnSeries(
        ticker=prices.ticker,
        returns=returns,
    )

def calculate_volatility(
    returns: ReturnSeries,
    periods_per_year: int = 252,
) -> VolatilityResult:
    """
    Calculate annualized volatility from periodic returns.

    Args:
        returns: Validated periodic return series.
        periods_per_year: Number of return periods per year.

    Returns:
        VolatilityResult containing annualized standard deviation.
    """

    values = [point.return_value for point in returns.returns]

    if len(values) < 2:
        raise ValueError("At least two returns are required.")

    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive.")

    mean = sum(values) / len(values)

    # Calculate sample variance(via bessel's correction) 
    variance = sum(
        (value - mean) ** 2 for value in values
    ) / (len(values) - 1)

    # annualize sample variance(multiplying by square root of periods_per_year).
    volatility = math.sqrt(variance) * math.sqrt(periods_per_year)

    return VolatilityResult(
        ticker=returns.ticker,
        observations=len(values),
        annualized_volatility=volatility,
    )

def calculate_max_drawdown(
    prices: HistoricalPrices,
) -> DrawdownResult:
    """
    Calculate maximum drawdown from historical adjusted prices.

    Use this tool when downside risk or historical loss from a
    previous peak is required.
    """

    if len(prices.bars) < 2:
        raise ValueError("At least two price observations are required.")

    peak = prices.bars[0].adj_close
    max_drawdown = 0.0

    for bar in prices.bars:
        peak = max(peak, bar.adj_close)
        drawdown = (bar.adj_close / peak) - 1
        max_drawdown = min(max_drawdown, drawdown)

    return DrawdownResult(
        ticker=prices.ticker,
        max_drawdown=max_drawdown,
    )


