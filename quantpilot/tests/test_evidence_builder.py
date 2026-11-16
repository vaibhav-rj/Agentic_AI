from src.agents.evidence_builder import build_evidence_ledger

# Incremental tests for the new LLM-based evidence assessment.
import json
from types import SimpleNamespace
from unittest.mock import patch

from src.agents.evidence_builder import assess_evidence_ledger
from src.schemas.evidence import Evidence, EvidenceLedger

"""
def main():
# ============================================================
# EXISTING MANUAL TEST / DEMONSTRATION
# ============================================================

    research_results = [
        {
            "step_id": 1,
            "tool_category": "market",
            "tool": "get_historical_prices",
            "result": {
                "ticker": "AAPL",
                "bars": [{"date": "2025-01-02"}],
            },
        },
        {
            "step_id": 2,
            "tool_category": "financial",
            "tool": "get_financial_metrics",
            "result": {
                "ticker": "AAPL",
                "metrics": [
                    {"name": "trailingPE", "value": 38.25},
                    {"name": "marketCap", "value": 4867743023104.0},
                ],
            },
        },
        {
            "step_id": 3,
            "tool_category": "quantitative",
            "tool": "quantitative_analysis",
            "result": {
                "total_return": {
                    "ticker": "AAPL",
                    "total_return": -0.0067,
                },
                "return_series": {
                    "ticker": "AAPL",
                    "returns": [{}, {}, {}],
                },
                "volatility": {
                    "ticker": "AAPL",
                    "annualized_volatility": 0.1439,
                },
                "max_drawdown": {
                    "ticker": "AAPL",
                    "max_drawdown": -0.0114,
                },
            },
        },
        {
            "step_id": 4,
            "tool_category": "research",
            "tool": "research_query",
            "result": {
                "query": "Compare Apple's returns and valuation.",
                "sources": [
                    {
                        "title": "Source 1",
                        "url": "https://example.com/1",
                        "content": "Research evidence 1.",
                    },
                    {
                        "title": "Source 2",
                        "url": "https://example.com/2",
                        "content": "Research evidence 2.",
                    },
                ],
            },
        },
    ]

    ledger = build_evidence_ledger(research_results)

    print(ledger)

    assert len(ledger.items) == 9

    assert any(
        e.source_type == "market_data" and e.source == "historical_prices"
        for e in ledger.items
    )

    assert sum(e.source_type == "financial_data" for e in ledger.items) == 2

    assert {
        e.source for e in ledger.items
        if e.source_type == "quantitative_analysis"
    } == {
        "total_return",
        "return_series",
        "volatility",
        "max_drawdown",
    }

    assert sum(e.source_type == "external_research" for e in ledger.items) == 2

    assert all(item.status == "SUPPORTED" for item in ledger.items)


if __name__ == "__main__":
    main()
"""

# ============================================================
# ADDITIONAL MOCK TESTS — NEW LLM HELPER FUNCTIONS
# ============================================================

def _sample_ledger():
    return EvidenceLedger(
        items=[
            Evidence(
                claim="AAPL historical price data was collected.",
                source_type="market_data",
                source="historical_prices",
                task_type="market_analysis",
                tool_category="market",
                evidence="10 price observations were collected.",
                confidence=0.99,
                status="SUPPORTED",
            )
        ]
    )


def _llm_response(assessments):
    return SimpleNamespace(
        content=json.dumps({"assessments": assessments})
    )


def test_assess_evidence_ledger_updates_status_and_confidence():
    ledger = _sample_ledger()

    with patch(
        "src.agents.evidence_builder.invoke_with_fallback",
        return_value=_llm_response([
            {
                "index": 0,
                "status": "PARTIALLY_SUPPORTED",
                "confidence": 0.65,
            }
        ]),
    ) as mock_llm:
        updated = assess_evidence_ledger(ledger)

    assert updated.items[0].status == "PARTIALLY_SUPPORTED"
    assert updated.items[0].confidence == 0.65
    assert updated.items[0].claim == ledger.items[0].claim
    assert updated.items[0].evidence == ledger.items[0].evidence

    # The original ledger must remain unchanged.
    assert ledger.items[0].status == "SUPPORTED"
    assert ledger.items[0].confidence == 0.99
    mock_llm.assert_called_once()


def test_assess_evidence_ledger_accepts_all_allowed_statuses():
    statuses = [
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "UNSUPPORTED",
        "CONFLICTING",
        "UNVERIFIED",
    ]
    ledger = EvidenceLedger(
        items=[
            _sample_ledger().items[0].model_copy()
            for _ in statuses
        ]
    )
    assessments = [
        {"index": i, "status": status, "confidence": i / 4}
        for i, status in enumerate(statuses)
    ]

    with patch(
        "src.agents.evidence_builder.invoke_with_fallback",
        return_value=_llm_response(assessments),
    ):
        updated = assess_evidence_ledger(ledger)

    assert [item.status for item in updated.items] == statuses
    assert [item.confidence for item in updated.items] == [
        0.0, 0.25, 0.5, 0.75, 1.0
    ]


def test_assess_evidence_ledger_returns_original_on_malformed_json():
    ledger = _sample_ledger()

    with patch(
        "src.agents.evidence_builder.invoke_with_fallback",
        return_value=SimpleNamespace(content="not JSON"),
    ):
        assert assess_evidence_ledger(ledger) is ledger


def test_assess_evidence_ledger_returns_original_on_invalid_assessment():
    ledger = _sample_ledger()

    invalid_assessments = [
        [{"index": 0, "status": "INVALID", "confidence": 0.5}],
        [{"index": 0, "status": "SUPPORTED", "confidence": 1.1}],
        [{"index": 0, "status": "SUPPORTED", "confidence": -0.1}],
        [{"index": True, "status": "SUPPORTED", "confidence": 0.5}],
        [{"index": 2, "status": "SUPPORTED", "confidence": 0.5}],
        [{"index": 0, "status": "SUPPORTED", "confidence": 0.5},
        {"index": 0, "status": "UNVERIFIED", "confidence": 0.2}],
        [],
    ]

    for assessments in invalid_assessments:
        with patch(
            "src.agents.evidence_builder.invoke_with_fallback",
            return_value=_llm_response(assessments),
        ):
            assert assess_evidence_ledger(ledger) is ledger


def test_assess_evidence_ledger_returns_original_on_llm_exception():
    ledger = _sample_ledger()

    with patch(
        "src.agents.evidence_builder.invoke_with_fallback",
        side_effect=RuntimeError("LLM unavailable"),
    ):
        assert assess_evidence_ledger(ledger) is ledger


def test_assess_evidence_ledger_skips_llm_for_empty_ledger():
    ledger = EvidenceLedger(items=[])

    with patch(
        "src.agents.evidence_builder.invoke_with_fallback"
    ) as mock_llm:
        assert assess_evidence_ledger(ledger) is ledger

    mock_llm.assert_not_called()