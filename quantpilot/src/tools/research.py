from src.schemas.research import ResearchResult
from src.tools.research_provider import search_research#this file not neede for othet tools:- market, finance, quant
#as yfinacnce is provider of 1st two and "quant" tool results are provided by opeartion on market tool o/p(HistoricalPrices)
#and return_series o/p(needed for volatility calc)

#def research(query: str) -> ResearchResult:
def research(research_query:str, original_query: str, max_results: int) -> ResearchResult:
    """Gather external research evidence for a query."""
    return search_research(research_query, original_query, max_results)

