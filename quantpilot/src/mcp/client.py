import asyncio
import json
#from src.schemas.market import HistoricalPrices
from mcp import ClientSession, StdioServerParameters
import src.config
from datetime import datetime, time

'''to import streamablehttp_client for connecting to the server hosted on http'''
#from mcp.client.streamable_http import streamablehttp_client  
from mcp.client.stdio import stdio_client

import sqlite3
from src.cache.tool_cache import ToolResultCache

import logging
from time import perf_counter

logger = logging.getLogger(__name__)


#lazily initialized cache instance
_tool_result_cache = None

def get_tool_result_cache():
    global _tool_result_cache

    if _tool_result_cache is None:
        try:
            _tool_result_cache = ToolResultCache()
        except (OSError, sqlite3.Error) as exc:
            print(f"Warning: Tool cache unavailable: {exc}")
            return None

    return _tool_result_cache

'''
To connect to this MCP server, start this Python process below to.So stdio needs the Python module path because the client launches the server.
HTTP(eg:- "http://localhost:8000/mcp")doesn't, because the server is already running independently. 
'''
async def connect_and_list_tools(module_name: str):
    server_params = StdioServerParameters(
        command="python",
        args=["-m", module_name],
    )

    '''
    Use stdio_client to connect to the MCP server over standard input/output(client sends MCP requests to the server via 
    write and receives MCP responses from the server via read).
    '''
    async with stdio_client(server_params) as (read, write):
    #async with streamable http_client("http://localhost:8000/mcp") as (read, write, _):#in case of server hosted on http
        async with ClientSession(read, write) as session:#Gives us the actual MCP server & client interface.
            await session.initialize()

            '''expose the tool.'''
            tools = await session.list_tools()

            print(f"\n{module_name}")
            for tool in tools.tools:
                print(f"- {tool.name}")
            

async def call_server(module_name, tool_name, arguments):

    # 1. Check persistent cache before launching the MCP server.
    cache = get_tool_result_cache()
    
    if cache is not None:
        try:
            #if not found, returns :-"None" (no exception)
            cached_result = cache.get(
                module_name, tool_name, arguments
            )
            if cached_result is not None:

                logger.info("MCP cache hit | tool=%s", tool_name)
                #print(f"result accesed from cache---{tool_name}----{arguments}")
                return cached_result
            
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            logger.warning("MCP cache read failed | tool=%s", tool_name, exc_info=True)
            #print(f"Warning: Cache read failed: {exc}")



    # 2. Cache miss: execute the MCP tool normally.
    server_params = StdioServerParameters(
        command="python",
        args=["-m", module_name],
    )

    #async with stdio_client(server_params, errlog=open("/tmp/quantpilot_mcp.log", "a"),) as (read, write):
    async with stdio_client(server_params, errlog=open("quantpilot_mcp.log", "a"),) as (read, write):

        try:
            async with ClientSession(read, write) as session:
                await session.initialize()

                '''Run the given tool with these arguments.'''
                started = perf_counter()
                logger.info("MCP tool call started | server=%s | tool=%s", module_name, tool_name)

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                '''modify result(MCP CallToolResult earlier) to json'''
                if result.is_error:
                    raise RuntimeError(
                        f"MCP tool '{tool_name}' failed: : {result.content}."
                    )

                content = result.content[0]

                if content.type != "text":
                    raise TypeError(
                        f"Expected text content from MCP tool '{tool_name}'."
                    )

                #return json.loads(content.text)
                parsed_result =json.loads(content.text)

                logger.info(
                    "MCP tool call completed | server=%s | tool=%s | duration=%.2fs",
                    module_name, tool_name, perf_counter() - started
                )
        except Exception:
            logger.exception(
                "MCP tool call failed | server=%s | tool=%s",
                module_name, tool_name
            )
            raise

    # 3. Cache only successfully parsed results.
    if cache is not None:
        try:
            cache.set(
                module_name, tool_name, arguments, parsed_result
            )
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            logger.warning("MCP cache write failed | tool=%s", tool_name, exc_info=True)
            #print(f"Warning: Cache write failed: {exc}")

    return parsed_result


async def main():
    #discover Market / Financial / Quant tools
    for module in [
        "src.mcp.market_server",
        "src.mcp.financial_server",
        "src.mcp.quant_server",
        "src.mcp.research_server"
    ]:
        '''
        using asyncio.run() not used in loops as that would create and destroy an event loop for every server.
        So rather "await" used inside an async function to run the connect_and_list_tools coroutine for each server module.
        '''
        await connect_and_list_tools(module)

    
    #call the historical_prices tool on the market server
    start_time = datetime.now()

    market_result = await call_server(
        "src.mcp.market_server",
        "historical_prices",
        {
            "ticker": "MSFT",#earlier:-"AAPL","NVDA","AMZN"(cahnge for tool result cache test 3)
            "start": "2025-01-01",
            "end": "2025-01-08",#(change for tool result cache test 4)
        },
    )

    print(f"\nmarket results:{'-'*80}")
    print(market_result)

    #call the financial_analysis tool on the financial server
    financial_result = await call_server(
        "src.mcp.financial_server",
        "financial_metrics",
        {
            "ticker": "MSFT",#earlier:-"AAPL","AMZN"
            "metrics": ["marketCap", "trailingPE", "profitMargins"],
        },
    )

    print(f"\nfinancial results:{'-'*80}")
    print(financial_result)

    #call the quant_analysis tool on the quant server
    '''
    content = market_result.content[0]

    if content.type != "text":
        raise TypeError("Expected text content from market MCP server.")
    
    market_data = json.loads(content.text)
    '''
    market_data= market_result  # Since market_result is already a dictionary fater transformation of MCP CallToolResult to json in call_server function.

    total_return_result = await call_server(
        "src.mcp.quant_server",
        "total_return",
        {"prices": market_data},
    )

    print(f"\ntotal return results:{'-'*80}")
    print(total_return_result)

    return_series_result = await call_server(
        "src.mcp.quant_server",
        "return_series",
        {"prices": market_data},
    )

    print(f"\nreturn series results:{'~'*80}")
    print(return_series_result)

    max_drawdown_result = await call_server(
        "src.mcp.quant_server",
        "max_drawdown",
        {"prices": market_data},
    )

    print(f"\nmax drawdown results:{'~'*80}")
    print(max_drawdown_result)

    ''''
    content = return_series_result.content[0]
    if content.type != "text":
        raise TypeError("Expected text content from return_series MCP server.")

    returns_data = json.loads(content.text)

    #print("Volatility input:")
    #print(json.dumps(returns_data, indent=2))
    '''

    returns_data= return_series_result  # Since return_series_result is already a dictionary fater transformation of MCP CallToolResult to json in call_server function.
    
    volatility_result = await call_server(
        "src.mcp.quant_server",
        "volatility",
        {"returns": returns_data},
    )

    print(f"\nVolatility results:{'~'*80}")
    print(volatility_result)

    reserach_query_result = await call_server(
        "src.mcp.research_server",
        "research_query",
        {"query": "NVIDIA AI chip market growth and competitive position"},
    )

    print(f"reserach_query_result:{'~'*80}")
    print(reserach_query_result)

    end_time =datetime.now()
    print(f"time_taken", end_time-start_time)


if __name__ == "__main__":
    asyncio.run(main())