from src.schemas.market import HistoricalPrices
from src.schemas.quant import ReturnSeries
from mcp.server.mcpserver import MCPServer

from src.tools.quant import (
    calculate_max_drawdown,
    calculate_return_series,
    calculate_total_return,
    calculate_volatility,
)

mcp = MCPServer("QuantPilot Quant Server")


@mcp.tool()
def total_return(prices: HistoricalPrices):
    """Calculate total return from validated historical prices."""

    return calculate_total_return(prices)


@mcp.tool()
def return_series(prices: HistoricalPrices):
    """Calculate periodic returns from validated historical prices."""

    return calculate_return_series(prices)


@mcp.tool()
def volatility(returns: ReturnSeries):
    """Calculate annualized volatility."""

    return calculate_volatility(returns)


@mcp.tool()
def max_drawdown(prices: HistoricalPrices):
    """Calculate maximum drawdown."""

    return calculate_max_drawdown(prices)


if __name__ == "__main__":
    mcp.run()