import yfinance as yf

from src.schemas.financials import FinancialMetric, FinancialMetrics


def get_financial_metrics(
    ticker: str,
    metrics: list[str],
) -> FinancialMetrics:
    """
    Retrieve requested financial metrics for a ticker.

    Use this tool when financial statement or valuation metrics
    are required for fundamental analysis.

    Args:
        ticker: Stock ticker symbol, such as "AAPL".
        metrics: Names of metrics to retrieve, such as
            "market_cap", "pe_ratio", or "revenue".

    Returns:
        FinancialMetrics containing the requested metrics.

    Raises:
        ValueError: If ticker is empty or no requested metrics are found.

    Limitations:
        Availability and accuracy depend on Yahoo Finance data.
        Missing metrics are returned with value=None.
    """

    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError("Ticker must not be empty.")

    if not metrics:
        raise ValueError("At least one metric must be requested.")

    #Fetching Real-time Info and Corporate Actions using Yahoo Finance API for given ticker 
    # using below.
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch financial information for {ticker}: {exc}"
        ) from exc

    results=[]
    #new addition after value_type scope expanded in schema
    for metric in metrics:
        raw_value = info.get(metric)

        if isinstance(raw_value, bool):
            value = raw_value
        elif isinstance(raw_value, (int, float, str)):
            value = raw_value
        elif raw_value is None:
            value = None
        else:
            value = str(raw_value)

        results.append(
            FinancialMetric(name=metric,value= value)
        )

        

    '''#inital value feed(when value could be float/int only) in o/p schema below 
    results = [
            FinancialMetric(
                name=metric,
                value=(
                        float(info[metric])
                        if info.get(metric) is not None
                        and isinstance(info.get(metric), (int, float))
                        else None
                    ),#new chnage after vlaues scope expansion'
            )
            for metric in metrics
        ]
    '''

    
    '''#removedto avoid disruption in workflow
    if all(metric.value is None for metric in results):
        raise ValueError(
            f"No requested financial metrics found for ticker '{ticker}'."
        )
    '''

    return FinancialMetrics(
        ticker=ticker,
        metrics=results,
    )