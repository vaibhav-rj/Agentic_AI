from .market import HistoricalPrices, PriceBar
from .financials import FinancialMetric, FinancialMetrics
from .quant import ReturnResult, ReturnPoint, ReturnSeries, VolatilityResult, DrawdownResult
from .query import ResearchQuery
from .research import ResearchStep, ResearchPlan, ResearchSource, ResearchResult
from .evidence import Evidence, EvidenceLedger
from .thesis import Thesis
from .critique import Critique
from .adjudication import Adjudication
from .final_report import FinalReport

__all__ = [
    "HistoricalPrices",
    "PriceBar",
    "FinancialMetric",
    "FinancialMetrics",
    "ReturnResult",
    "ReturnPoint",
    "ReturnSeries",
    "VolatilityResult",
    "DrawdownResult",
    "ResearchQuery",
    "ResearchStep",
    "ResearchPlan",
    "Evidence",
    "EvidenceLedger",
    "ResearchSource", 
    "ResearchResult",
    "Thesis",
    "Critique",
    "Adjudication",
    "FinalReport",
]

'''
above internal module calling for refering classes of (schemas/market.py) in the __init__.py file of the schemas package. 
for public interface(outside the package):- "from src.schemas import HistoricalPrices, PriceBar" works fine. same format
for other classes of the schemas package. This __init__.py file is used to create a clean public package API, helps in 
hiding internal implementation details, and allows for better maintainablity and recfactoring of the codebase. It also 
enables users to import only the necessary functions or classes without exposing the entire module structure.
'''  