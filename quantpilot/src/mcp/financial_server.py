from mcp.server.mcpserver import MCPServer

from src.tools.financials import get_financial_metrics

mcp = MCPServer("QuantPilot Financial Server")


@mcp.tool()
def financial_metrics(
    ticker: str,
    metrics: list[str],
):
    """Get requested financial metrics for a ticker."""

    return get_financial_metrics(
        ticker=ticker,
        metrics=metrics,
    )


if __name__ == "__main__":
    mcp.run()