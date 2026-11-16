import re 

from src.schemas.query import ResearchQuery
from src.llm import invoke_with_fallback# Routes query analysis through the gateway with model-failure fallback.
import json  # Parses the model's JSON response.
from datetime import date, timedelta
from langchain_core.messages import SystemMessage, HumanMessage

import logging

logger = logging.getLogger(__name__)

def analyze_query_heuristic(query: str) -> ResearchQuery:
    """Analyze a validated research query."""

    words = set(re.findall(r"\b\w+\b", query.lower()))

    task_types = []

    if words & {"compare", "versus", "vs"}:
        task_types.append("comparison")

    if words & {
        "revenue",
        "profit",
        "earnings",
        "valuation",
        "pe",
        "fundamentals",
    }:
        task_types.append("financial_analysis")

    if words & {
        "return",
        "returns",
        "volatility",
        "drawdown",
        "correlation",
        "beta",
    }:
        task_types.append("quantitative_analysis")

    if not task_types:
        task_types.append("market_analysis")

    entities = re.findall(
        r"\b[A-Z]{1,5}\b",
        query,
    )

    metrics = []

    metric_keywords = {
        "revenue",
        "profit",
        "earnings",
        "valuation",
        "pe",
        "marketcap",
        "return",
        "returns",
        "volatility",
        "drawdown",
        "correlation",
        "beta",
    }

    for word in words:
        if word in metric_keywords:
            metrics.append(word)

    time_horizon = None

    time_match = re.search(
        r"\b(?:20\d{2}(?:\s*-\s*20\d{2})?|"
        r"last\s+\d+\s+(?:days?|weeks?|months?|years?)|"
        r"past\s+\d+\s+(?:days?|weeks?|months?|years?))\b",
        query.lower(),
    )

    if time_match:
        time_horizon = time_match.group(0)

    return ResearchQuery(
        original_query=query,
        task_types=task_types,
        entities=entities,
        research_questions=[query],
        metrics=metrics,
        time_horizon=time_horizon,
    )

# LLM extracts semantic information; Python validates its output.
def analyze_query_with_context(
    query: str,
    ticker: str,
    default_start: date,
    default_end: date,
) -> tuple[ResearchQuery, date, date]:
    heuristic = analyze_query_heuristic(query)

    messages = [
        SystemMessage(content="""
    You are QuantPilot's query-analysis component.

    Analyze the user's query and return ONLY a JSON object containing:
    - task_types: list chosen from market_analysis, financial_analysis,
    quantitative_analysis, comparison (between 2 or more of these task_types).
    - task_types can qualify for one or more individual task_type, so create an exhaustive list.
    - entities: relevant company names, tickers, and named subjects
    - research_questions: specific, answerable research questions
    - date_status: none, resolved, ambiguous, or invalid
    - start_date: ISO YYYY-MM-DD or null
    - end_date_exclusive: ISO YYYY-MM-DD or null

    Note:-Don't exceed 512 output tokens in any case but also accomodate all the fields of the JSON.

    Rules:
    1. Do not invent entities, dates, or financial metrics.
    2. If no time period is specified, use date_status "none".
    3. Resolve explicit dates and relative durations using the current date.
    4. Recognize financial periods such as first quarter, first trimester,
    latter half, and similar expressions. If the year or fiscal/calendar
    convention materially affects interpretation, mark ambiguous.
    5. Explicit date ranges include their stated final day. Convert that
    final day to the following day for end_date_exclusive.
    6. For a duration such as "starting 3 March for two months", resolve
    the end according to the stated duration.
    7. If an explicitly stated date is invalid, mark it invalid.
    8. Do not calculate financial metrics or alter supplied defaults.

    Return valid JSON only. Follow the schema exactly.
    """),
        HumanMessage(content=f"""
    Current date: {date.today().isoformat()}
    Supplied ticker: {ticker}
    Default start date: {default_start.isoformat()}
    Default end date (exclusive): {default_end.isoformat()}

    User query: {query}
    """)
    ]

    try:
        response = invoke_with_fallback("reasoning", messages)

        content = response.content

        #check whether o/p is not none
        if not isinstance(content, str):
            raise ValueError("Expected a text response")

        #print(f"content(repr):-{repr(content)}")
        logger.debug("Query-analysis response received")
        data = json.loads(content)

        # Validate semantic fields while retaining deterministic metrics.
        allowed_types = {
            "market_analysis",
            "financial_analysis",
            "quantitative_analysis",
            "comparison",
            #"mixed",
        }
        task_types = data["task_types"]
        entities = data["entities"]
        questions = data["research_questions"]

        if (
            not isinstance(task_types, list)
            or not task_types
            or not set(task_types).issubset(allowed_types)
            or not isinstance(entities, list)
            or not all(isinstance(x, str) for x in entities)
            or not isinstance(questions, list)
            or not questions
            or not all(isinstance(x, str) and x.strip() for x in questions)
        ):
            raise ValueError("Invalid query-analysis fields")

        research_query = heuristic.model_copy(
            update={
                "task_types": task_types,
                "entities": list(dict.fromkeys([*entities, ticker])),
                "research_questions": questions,
            }
        )

        # Keep caller-supplied dates unless a valid period was extracted.
        if data["date_status"] == "none":
            start, end = default_start, default_end

        elif data["date_status"] == "resolved":
            start = date.fromisoformat(data["start_date"])
            end = date.fromisoformat(data["end_date_exclusive"])

            if start >= end:
                raise ValueError("Resolved start date must precede end date")

        elif data["date_status"] == "ambiguous":
            # Preserve defaults rather than silently guessing.
            start, end = default_start, default_end

        elif data["date_status"] == "invalid":
            raise ValueError("The query specifies an invalid date range")

        else:
            raise ValueError("Unknown date extraction status")

        # Keep time_horizon consistent with the effective execution dates.
        time_horizon = (
            f"{start.isoformat()} to {(end - timedelta(days=1)).isoformat()}"
        )
        research_query = research_query.model_copy(
            update={"time_horizon": time_horizon}
        )

        return research_query, start, end

    except ValueError as exc:
        # Explicit date errors must not be hidden by heuristic fallback.
        if str(exc) in {
            "The query specifies an invalid date range",
            "Resolved start date must precede end date",
        }:
            raise

        logger.warning("LLM query analysis failed; using heuristic fallback", exc_info=True)
        return heuristic.model_copy(
            update={"entities": list(dict.fromkeys([*heuristic.entities, ticker]))}
        ), default_start, default_end

    except Exception:
        # LLM/provider/JSON failures retain the existing deterministic path.

        logger.warning("LLM query analysis failed; using heuristic fallback", exc_info=True)
        return heuristic.model_copy(
            update={"entities": list(dict.fromkeys([*heuristic.entities, ticker]))}
        ), default_start, default_end


# Backward-compatible entry point for existing callers and tests.
def analyze_query(query: str) -> ResearchQuery:
    return analyze_query_heuristic(query)