from src.schemas.adjudication import Adjudication
from src.schemas.research import ResearchPlan, ResearchStep
from src.schemas.query import ResearchQuery
from src.schemas.evidence import EvidenceLedger

from typing import Literal, TypeAlias, cast
import re

import logging

logger = logging.getLogger(__name__)

#the 2nd finacial(tool_cat) has been 
#added in value of task_types(financial_analysis)to (i)cover the dynamic financial metric 
# are generated from query when neither quantitaive/research_analysis are present but 
# comparative task_type .(ii) forgotton explicit metrics for financial_analysis only query;
# and we'll like yfinance.info on dynamic finance metric,

REPLAN_TASK_TO_TOOLS = {
    "market_analysis": {"market", "financial", "research"},
    "financial_analysis": {"financial", "research", "financial"}, 
    "quantitative_analysis": {"market", "quantitative", "financial"},
    "comparison": {"market", "financial", "quantitative", "research"},
    "mixed": {"market", "financial", "quantitative", "research"},
}

ToolCategory: TypeAlias = Literal[
    "market",
    "financial",
    "quantitative",
    "research",
]

category_map = {
    "market": "Collect the missing market evidence.",
    "financial": "Collect the missing financial evidence.",
    "quantitative": "Perform the missing quantitative analysis.",
    "research": "Gather the missing external research evidence.",
}

YFINANCE_INFO_METRICS= set([
    "address1", "address2", "city", "state", "zip", "country", "phone", "website",
    "industry", "industryKey", "sector", "sectorKey", "longBusinessSummary", "fullTimeEmployees",
    "companyOfficers", "auditRisk", "boardRisk", "compensationRisk", "shareHolderRightsRisk", "overallRisk",
    "currentPrice", "open", "dayLow", "dayHigh", "regularMarketPreviousClose", "regularMarketOpen",
    "regularMarketDayLow", "regularMarketDayHigh", "previousClose", "volume", "regularMarketVolume",
    "averageVolume", "averageVolume10days", "averageDailyVolume10Day", "bid", "ask", "bidSize", "askSize",
    "exchanges", "exchange", "market", "quoteType", "symbol", "currency", "timeZoneFullName",
    "timeZoneShortName", "gmtOffSetMilliseconds", "marketCap", "enterpriseValue", "trailingPE",
    "forwardPE", "pegRatio", "priceToSalesTrailing12Months", "priceToBook", "enterpriseToRevenue",
    "enterpriseToEbitda", "totalRevenue", "revenuePerShare", "revenueGrowth", "grossProfits", "ebitda",
    "netIncomeToCommon", "trailingEps", "forwardEps", "grossMargins", "operatingMargins", "ebitdaMargins",
    "profitMargins", "totalCash", "totalCashPerShare", "totalDebt", "debtToEquity", "currentRatio",
    "quickRatio", "bookValue", "operatingCashflow", "freeCashflow", "returnOnAssets", "returnOnEquity",
    "sharesOutstanding", "impliedSharesOutstanding", "floatShares", "sharesShort", "sharesShortPriorMonth",
    "sharesShortDirection", "shortRatio", "shortPercentOfFloat", "heldPercentInsiders", "heldPercentInstitutions",
    "dividendRate", "dividendYield", "payoutRatio", "trailingAnnualDividendRate", "trailingAnnualDividendYield",
    "fiveYearAvgDividendYield", "lastDividendValue", "lastDividendDate", "lastSplitFactor", "lastSplitDate",
    "underlyingSymbol", "fiftyTwoWeekLow", "fiftyTwoWeekHigh", "fiftyTwoWeekChange", "SandP52WeekChange",
    "fiftyDayAverage", "twoHundredDayAverage", "beta"
])

def find_financial_metrics(query: str) -> list[str]:
    normalized_query = re.sub(r"[\s_-]+", "", query.lower())

    return [
        metric
        for metric in YFINANCE_INFO_METRICS
        if re.sub(r"[\s_-]+", "", metric.lower()) in normalized_query
    ]


def replan_research(
    research_query: ResearchQuery,
    evidence: EvidenceLedger,
    adjudication: Adjudication,
) -> tuple[ResearchPlan, list[str]]:
    
    if not adjudication.evidence_debt:
        raise ValueError("Evidence debt is required for re-planning")

    financial_metrics = find_financial_metrics(research_query.original_query)#dynamic f_metrocs 
    #for task_types='market_analysis/quantitaive_analysis' 

    steps: list[ResearchStep] = []
    step_id = 1

    planned_pairs: set[tuple[str, str]] = set()#added to handle duplication of tool_category from new
    #adjudication.evidence_dbet(for missing evidence-->both task_type and tool_category together)

    for debt in adjudication.evidence_debt:
        match = re.search(
            r"Missing (\w+) evidence for ([\w_]+)\.",
            debt,
            re.IGNORECASE,
        )

        if match:
            category = match.group(1).lower()
            task_type = match.group(2).lower()

            if (
                task_type not in research_query.task_types
                or category not in category_map
                or (task_type, category) in planned_pairs
            ):
                continue

        else:
            # Challenged evidence: retry only when its source is identifiable.
            source_match = re.search(
                r"(?:Unsupported|Partially supported|Conflicting|Unverified|Low-confidence) evidence: (.+)",
                debt,
                re.IGNORECASE,
            )
            if not source_match:
                continue

            claim = source_match.group(1)
            matching_items = [
                item for item in evidence.items
                if item.claim == claim
            ]
            if not matching_items:
                continue

            item = matching_items[0]
            task_type = item.task_type
            category = item.tool_category

            if (
                task_type not in research_query.task_types
                or category not in category_map
                or (task_type, category) in planned_pairs
            ):
                continue

        if (
            category == "financial"
            #and task_type != "financial_analysis"(removed to run dynamic finnacial metric even with financial analysis in replan run)
            and not financial_metrics
        ):
            
            steps.append(
                ResearchStep(
                    step_id= step_id,
                    task_type=task_type,
                    tool_category="financial",
                    objective=category_map[category],
                    required=False,
                )
            )
            step_id += 1
            continue

        steps.append(
            ResearchStep(
                step_id=step_id,
                task_type=task_type,
                tool_category=cast(ToolCategory, category),
                objective=category_map[category],
                required=True,
            )
        )
        planned_pairs.add((task_type, category))
        step_id += 1

    if not steps:
        raise ValueError(
            "Evidence debt does not identify a re-plannable tool category"
        )

    logger.info("Replan created | steps=%d | financial_metrics=%s", len(steps), financial_metrics)

    return ResearchPlan(
        query=research_query.original_query,
        steps=steps,
        research_questions=research_query.research_questions,
    ), financial_metrics