'''
MCP contract and server boundary without pretending we have a research provider/tool yet.
'''
import src.config
from mcp.server.mcpserver import MCPServer
from src.tools.research import research

mcp = MCPServer("QuantPilot Research Server")

'''
@mcp.tool()
def research_query(research_query: str, original_query: str='', max_results: int=5):
    """Gather external research evidence for a query."""
    return research(research_query=research_query, original_query=original_query, max_results=max_results)
'''

@mcp.tool()
def research_query(research_query: str, original_query: str = "", max_results: int = 5):
    try:
        print("MCP RECEIVED:", research_query, original_query, max_results, flush=True)
        return research(
            research_query=research_query,
            original_query=original_query,
            max_results=max_results,
        )
    except Exception as e:
        import traceback
        print(f"RESEARCH SERVER ERROR: {e}", flush=True)
        traceback.print_exc()
        raise



if __name__ == "__main__":
    mcp.run(transport="stdio")