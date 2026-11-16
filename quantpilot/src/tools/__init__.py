from .market import get_historical_prices
from .financials import get_financial_metrics
from .quant import calculate_total_return, calculate_return_series, calculate_volatility, calculate_max_drawdown
from .research import research

__all__ = [
    "get_historical_prices",
    "get_financial_metrics",
    "calculate_total_return",
    "calculate_return_series",
    "calculate_volatility",
    "calculate_max_drawdown",
    "research",
]

'''
above internal module calling for refering classes of (schemas/market.py) in the __init__.py file of the schemas package.
for public interface(outside the package):- "from src.tools import get_historical_prices" works fine. Same format for 
other classes of the tools package. This __init__.py file is used to create a clean public package API, helps in hiding
internal implementation details, and allows for better maintainablity and recfactoring of the codebase. It also enables 
users to import only the necessary functions or classes without exposing the entire module structure.
'''