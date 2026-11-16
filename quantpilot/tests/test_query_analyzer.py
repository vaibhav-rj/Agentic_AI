from src.agents import query_analyzer
from src.agents.query_analyzer import analyze_query
import json
from datetime import date
from types import SimpleNamespace

import pytest

'''
def main():
    result = analyze_query(
        "Analyze Apple's historical volatility."
    )
    print(result)

    result = analyze_query(
        "Compare Apple's revenue growth and valuation."
    )
    print(result)


    assert analyze_query(
        "Analyze Apple's historical volatility."
    ).task_types == ["quantitative_analysis"]

    assert analyze_query(
        "Analyze Apple's revenue, profit, and valuation."
    ).task_types == ["financial_analysis"]

    assert analyze_query(
        "Compare Apple's returns and valuation."
    ).task_types == [
        "comparison",
        "financial_analysis",
        "quantitative_analysis",
    ]

    assert analyze_query(
        "What is the correlation between profit and valuation of AAPL?"
    ).task_types == [
        "financial_analysis",
        "quantitative_analysis",
    ]


if __name__ == "__main__":
    main()
'''

START = date(2025, 1, 1)
END = date(2025, 1, 8)
TICKER = "AAPL"


def mock_response(data):
    return SimpleNamespace(content=json.dumps(data))


def valid_payload(**overrides):
    data = {
        "task_types": ["quantitative_analysis"],
        "entities": ["Apple"],
        "research_questions": ["Analyze Apple's volatility."],
        "date_status": "none",
        "start_date": None,
        "end_date_exclusive": None,
    }
    data.update(overrides)
    return data


def test_analyzer_accepts_valid_llm_output(monkeypatch):
    monkeypatch.setattr(
        query_analyzer,
        "invoke_with_fallback",
        lambda *args, **kwargs: mock_response(valid_payload()),
    )

    result, start, end = query_analyzer.analyze_query_with_context(
        "Analyze Apple's volatility.", TICKER, START, END
    )

    assert result.task_types == ["quantitative_analysis"]
    assert "Apple" in result.entities
    assert TICKER in result.entities
    assert result.research_questions == ["Analyze Apple's volatility."]
    assert (start, end) == (START, END)


def test_analyzer_falls_back_on_malformed_json(monkeypatch):
    monkeypatch.setattr(
        query_analyzer,
        "invoke_with_fallback",
        lambda *args, **kwargs: SimpleNamespace(content="not valid JSON"),
    )

    result, start, end = query_analyzer.analyze_query_with_context(
        "Analyze Apple's volatility.", TICKER, START, END
    )

    assert "quantitative_analysis" in result.task_types
    assert TICKER in result.entities
    assert (start, end) == (START, END)


def test_analyzer_falls_back_on_invalid_semantic_fields(monkeypatch):
    monkeypatch.setattr(
        query_analyzer,
        "invoke_with_fallback",
        lambda *args, **kwargs: mock_response(
            valid_payload(task_types=["unsupported_task"])
        ),
    )

    result, start, end = query_analyzer.analyze_query_with_context(
        "Analyze Apple's volatility.", TICKER, START, END
    )

    assert "quantitative_analysis" in result.task_types
    assert TICKER in result.entities
    assert (start, end) == (START, END)


def test_analyzer_falls_back_when_gateway_raises(monkeypatch):
    def fail_gateway(*args, **kwargs):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(query_analyzer, "invoke_with_fallback", fail_gateway)

    result, start, end = query_analyzer.analyze_query_with_context(
        "Analyze Apple's volatility.", TICKER, START, END
    )

    assert "quantitative_analysis" in result.task_types
    assert TICKER in result.entities
    assert (start, end) == (START, END)


def test_analyzer_rejects_explicitly_invalid_date(monkeypatch):
    monkeypatch.setattr(
        query_analyzer,
        "invoke_with_fallback",
        lambda *args, **kwargs: mock_response(
            valid_payload(date_status="invalid")
        ),
    )

    with pytest.raises(ValueError, match="invalid date range"):
        query_analyzer.analyze_query_with_context(
            "Analyze Apple's volatility for an invalid period.",
            TICKER,
            START,
            END,
        )


def test_analyzer_uses_resolved_date_range(monkeypatch):
    monkeypatch.setattr(
        query_analyzer,
        "invoke_with_fallback",
        lambda *args, **kwargs: mock_response(
            valid_payload(
                date_status="resolved",
                start_date="2025-02-01",
                end_date_exclusive="2025-03-01",
            )
        ),
    )

    result, start, end = query_analyzer.analyze_query_with_context(
        "Analyze Apple's volatility in February 2025.", TICKER, START, END
    )

    assert start == date(2025, 2, 1)
    assert end == date(2025, 3, 1)
    assert result.time_horizon == "2025-02-01 to 2025-02-28"
