from datetime import date

#from mcp.server.fastmcp import FastMCP
from mcp.server.mcpserver import MCPServer

from src.tools.market import get_historical_prices

mcp = MCPServer("QuantPilot Market Server")
'''
Here no need to import HistoricalPrices and PriceBar from src.schemas.market because they are already defined in market.py
and get_historical_prices function returns HistoricalPrices object which contains list of PriceBar objects. 
So we can directly use the get_historical_prices function to get the historical prices data. The MCPServer is 
initialized(in place of FastMCP) with the name "QuantPilot Market Server", 
and the historical_prices function is decorated with @mcp.tool() to expose it as a tool in the server. 
The main block runs the server when the script is executed directly.
'''

@mcp.tool()
def historical_prices(
    ticker: str,
    start: date,
    end: date,
):
    """Get validated historical OHLCV price data for a ticker."""

    return get_historical_prices(
        ticker=ticker,
        start=start,
        end=end,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")# when server hosted on stdio, although mcp.run() defaults to same
    #mcp.run(transport="streamable-http")#In case of server hosted on http