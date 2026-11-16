import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp.types import TextContent
import pytest


load_dotenv()

@pytest.mark.asyncio
async def test_research_pipeline():

    if not os.getenv("TAVILY_API_KEY"):
        raise ValueError("TAVILY_API_KEY is not configured.")

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp.research_server"],
    )

    # Test 1: Initial research
    initial_args = {
        "research_query": (
            (' ').join(["What is Apple's current valuation relative to its "
            'historical averages and peers?',
            'What are the recent market trends for Apple stock?']).strip()            
        ),
        "max_results": 5,
    }

    # Test 2: Replan research
    replan_args = {
        "research_query": (
            (' ').join(["What is Apple's current valuation relative to its "
            'historical averages and peers?',
            'What are the recent market trends for Apple stock?']).strip()
        ),
        "original_query": "Analyze Apple's valuation, and market trend.",
        "max_results": 5,
    }


    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            tools = await session.list_tools()
            for tool in tools.tools:
                if tool.name == "research_query":
                    print(f"- {tool.name}")

            for label, arguments in [
                ("INITIAL RESEARCH", initial_args),
                ("REPLAN RESEARCH", replan_args),
            ]:

                print(f"\n========== {label} ==========")

                print("REPLAN ARGUMENTS:", arguments, flush=True)

                try:
                    result = await session.call_tool("research_query", arguments=arguments)
                    #print("RAW MCP RESULT:", repr(result), flush=True)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    raise

                #result = await session.call_tool("research_query",arguments=arguments,)

                if result.is_error:
                    raise RuntimeError(f"{label} failed: {result.content}")

                for item in result.content:
                    if isinstance(item, TextContent):
                        print(item.text)

                print(f"\n{label} completed successfully.")

if __name__ == "main":
    asyncio.run(test_research_pipeline())