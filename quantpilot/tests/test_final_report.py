from src.agents.final_report import generate_final_report
from src.schemas.adjudication import Adjudication
from src.schemas.evidence import Evidence, EvidenceLedger
from src.schemas.thesis import Thesis

import json
from types import SimpleNamespace

from src.agents import final_report

"""
user_query = "Compare Apple's returns and valuation."

research_plan = [
    ResearchStep(
        step_id="step_1",
        task_type="market_analysis",
        tool_category="market",
        objective="Fetch Apple's historical prices and analyze returns.",
        required=True,
    ),
    ResearchStep(
        step_id="step_2",
        task_type="financial_analysis",
        tool_category="financial",
        objective="Retrieve Apple's valuation metrics.",
        required=True,
    ),
]

research_results = [
    {
        "step_id": "step_1",
        "task_type": "market_analysis",
        "tool_category": "market",
        "tool": "historical_prices",
        "result": {"ticker": "AAPL", "prices": []},
    },
    {
        "step_id": "step_2",
        "task_type": "financial_analysis",
        "tool_category": "financial",
        "tool": "financial_metrics",
        "result": {"ticker": "AAPL", "metrics": []},
    },
]

evidence = EvidenceLedger(
    items=[
        Evidence(
            claim="AAPL historical price data was collected.",
            source_type="market_data",
            source="historical_prices",
            task_type ="market_analysis",
            tool_category="market",
            evidence="4 price observations were collected.",
            confidence=0.99,
            status="SUPPORTED",
        ),
        Evidence(
            claim="AAPL has a reported trailingPE value.",
            source_type="financial_data",
            source="financial_metrics",
            task_type ="finacial_analysis",
            tool_category="financial",
            evidence="trailingPE = 38.38188.",
            confidence=0.95,
            status="SUPPORTED",
        ),
    ]
)

thesis = Thesis(
    thesis="Apple generated positive returns while maintaining a measurable valuation.",
    supporting_evidence=[
        "Apple generated positive returns.",
        "Apple has a measurable valuation multiple.",
    ],
    confidence=0.8,
)

adjudication = Adjudication(
    decision="PASS",
    rationale="The thesis has sufficient supporting evidence.",
    evidence_debt=[],
    confidence=0.8,
)

research_plan={}

result = generate_final_report(
    user_query
    thesis,
    #evidence,
    adjudication,
    research_plan,
    research_results,
)

print(result)
"""


def test_refine_report_narrative_success(monkeypatch):
    expected = {
        "summary": "Refined summary.",
        "conclusion": "Refined conclusion.",
    }

    def mock_llm(model, messages):
        prompt = messages[1].content
        assert "AAPL" in prompt
        return SimpleNamespace(content=json.dumps(expected))

    monkeypatch.setattr(final_report, "invoke_with_fallback", mock_llm)

    summary, conclusion = final_report._refine_report_narrative(
        user_query="Analyze AAPL",
        thesis="Initial thesis",
        conclusion="Initial rationale",
        normalized_results=[{"tool_category": "market", "result": {"price": 200}}],
        limitations=[],
    )

    assert summary == expected["summary"]
    assert conclusion == expected["conclusion"]


def test_refine_report_narrative_invalid_json_fallback(monkeypatch):
    monkeypatch.setattr(
        final_report,
        "invoke_with_fallback",
        lambda *args: SimpleNamespace(content="invalid JSON"),
    )

    summary, conclusion = final_report._refine_report_narrative(
        "Analyze AAPL", "Initial thesis", "Initial rationale", [], []
    )

    assert summary == "Initial thesis"
    assert conclusion == "Initial rationale"


def test_refine_report_narrative_exception_fallback(monkeypatch):
    def mock_llm(*args):
        raise RuntimeError("Simulated LLM failure")

    monkeypatch.setattr(final_report, "invoke_with_fallback", mock_llm)

    summary, conclusion = final_report._refine_report_narrative(
        "Analyze AAPL", "Initial thesis", "Initial rationale", [], []
    )

    assert summary == "Initial thesis"
    assert conclusion == "Initial rationale"