from src.agents.thesis_generator import generate_thesis
from src.schemas.evidence import Evidence, EvidenceLedger

import json
from types import SimpleNamespace
from unittest.mock import patch

from src.agents.thesis_generator import generate_thesis
from src.schemas.evidence import Evidence, EvidenceLedger

"""
def main():
    evidence = EvidenceLedger(items=[
        Evidence(
            claim="AAPL had a measured total return over the analyzed period.",
            source_type="quantitative_analysis",
            source="total_return",
            evidence="Total return = -0.6725%.",
            confidence=0.99,
            status="SUPPORTED",
        ),
        Evidence(
            claim="AAPL has a reported trailingPE value.",
            source_type="financial_data",
            source="financial_metrics",
            evidence="trailingPE = 38.25.",
            confidence=0.95,
            status="SUPPORTED",
        ),
    ])

    result = generate_thesis(
        user_query="Compare Apple's returns and valuation.",
        evidence=evidence,
    )

    print(result)

    assert result.thesis
    assert len(result.supporting_evidence) == 2
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0


if __name__ == "__main__":
    main()
"""

def _sample_ledger():
    return EvidenceLedger(items=[
        Evidence(
            claim="AAPL has strong returns.",
            source_type="market_data",
            source="test source",
            evidence="AAPL returned 8% over the period.",
            task_type="quantitative_analysis",
            tool_category="market",
            confidence=0.95,
            status="SUPPORTED",
        ),
        Evidence(
            claim="AAPL's outlook is uncertain.",
            source_type="external_research",
            source="test source 2",
            evidence="The outlook remains uncertain.",
            task_type="research",
            tool_category="research",
            confidence=0.6,
            status="CONFLICTING",
        ),
    ])


def test_generate_thesis_uses_llm_and_keeps_evidence_lists_deterministic():
    ledger = _sample_ledger()
    response = SimpleNamespace(content=json.dumps({
        "thesis": "AAPL showed positive returns, although its outlook remains uncertain.",
        "confidence": 0.72,
    }))

    with patch(
        "src.agents.thesis_generator.invoke_with_fallback",
        return_value=response,
    ) as mock_llm:
        result = generate_thesis("Analyze AAPL.", ledger)

    mock_llm.assert_called_once_with("judge", mock_llm.call_args.args[1])
    assert result.thesis.startswith("AAPL showed positive returns")
    assert result.confidence == 0.72
    assert result.supporting_evidence == [
        "AAPL returned 8% over the period."
    ]
    assert result.contradicting_evidence == [
        "The outlook remains uncertain."
    ]


def test_generate_thesis_falls_back_on_invalid_llm_response():
    ledger = _sample_ledger()

    with patch(
        "src.agents.thesis_generator.invoke_with_fallback",
        return_value=SimpleNamespace(content="not valid JSON"),
    ):
        result = generate_thesis("Analyze AAPL.", ledger)

    assert result.thesis == "Research findings were collected for: Analyze AAPL."
    assert result.confidence == 0.5
    assert len(result.supporting_evidence) == 1
    assert len(result.contradicting_evidence) == 1


def test_generate_thesis_falls_back_on_llm_exception():
    with patch(
        "src.agents.thesis_generator.invoke_with_fallback",
        side_effect=RuntimeError("LLM unavailable"),
    ):
        result = generate_thesis("Analyze AAPL.", _sample_ledger())

    assert result.thesis == "Research findings were collected for: Analyze AAPL."
    assert result.confidence == 0.5


def test_generate_thesis_with_empty_ledger_skips_llm():
    with patch("src.agents.thesis_generator.invoke_with_fallback") as mock_llm:
        result = generate_thesis("Analyze AAPL.", EvidenceLedger(items=[]))

    mock_llm.assert_not_called()
    assert result.confidence == 0.5
    assert result.supporting_evidence == []
    assert result.contradicting_evidence == []