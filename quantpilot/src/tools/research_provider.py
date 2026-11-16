import re
import os
from tavily import TavilyClient
from src.schemas.research import ResearchResult, ResearchSource

import sys
import io

#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",errors="replace",line_buffering=True,)


def search_research(research_query: str, original_query:str, max_results: int) -> ResearchResult:
    """Search external sources and retain the most relevant result."""

    print("DEBUG:", research_query, original_query, max_results, flush=True)

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not configured.")

    client = TavilyClient(api_key=api_key)

    # Strengthen financial/company-specific search intent.
    
    if(original_query):
        '''
        search_query= (
            f"{original_query}. Answer in relevance to company economic and financial performance, "\
            f"valuation, and relevant market context. Additional research context: {research_query}"
        )'''

        
        search_query = (
            f"{original_query}. {research_query}. Answer in relevance to company's economic and financial performance, "\
            f"valuation, and relevant market context."
        )

    else:
        search_query = (
            f"{research_query}. Answer in relevance to company economic and financial performance, "\
            f"valuation, and relevant market context."
        )

    response = client.search(
        query=search_query,
        search_depth="advanced",
        max_results=max_results,
    )

    results = response.get("results", [])

    '''
    query_terms = set(re.findall(r"\b[a-zA-Z0-9]+\b", query.lower()))

    def relevance_score(result: dict) -> int:
        text = " ".join([
            result.get("title", ""),
            result.get("content", ""),
            result.get("url", ""),
        ]).lower()
        terms = set(re.findall(r"\b[a-zA-Z0-9]+\b", text))
        return len(query_terms & terms)

    best_result = max(results, key=relevance_score, default=None)
    '''

    #new section afetr above commented(to check incremental max_results=10)
    print("\n========== TAVILY RAW RESULTS ==========", flush=True)
    print(f"Query: {search_query}", flush=True)
    print(f"Requested max_results: {max_results}", flush=True)
    print(f"Results returned: {len(results)}", flush=True)

    #query_terms = set(re.findall(r"\b[a-zA-Z0-9]+\b", query.lower()))


    for i, result in enumerate(results, 1):
        print(f"\n--- RESULT {i} ---", flush=True)
        print(f"Title: {result.get('title')}", flush=True)
        print(f"URL: {result.get('url')}", flush=True)
        print(f"Tavily score: {result.get('score')}", flush=True)
        #print(f"Our lexical score: {relevance_score(result)}", flush=True)
        #print(f"Content: {result.get('content', '')[:500]}", flush=True)
        print(
            f"Content: {result.get('content', '')[:500]}".encode(
                "ascii", errors="backslashreplace"
            ).decode("ascii"),
            file=sys.stderr,
            flush=True,
        )

    best_result = max(results, key=lambda result: result.get("score", 0), default=None)

    print("\n--- SELECTION ---", flush=True)
    if best_result:
        print(f"Selected: {best_result.get('title')}", flush=True)
        print(f"Selected tavily score: {best_result.get('score')}", flush=True)
    else:
        print("No result selected.", flush=True)
    print("========================================\n", flush=True)
    #new section(to check incremental max_results=10) working ends

    sources = []
    #if best_result and relevance_score(best_result) > 0:
    if best_result:
        sources.append(
            ResearchSource(
                title=best_result["title"],
                url=best_result["url"],
                content=best_result["content"],
            )
        )

    return ResearchResult(
        query=original_query or research_query,
        sources=sources,
    )