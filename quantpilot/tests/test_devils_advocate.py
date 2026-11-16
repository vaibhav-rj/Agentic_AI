from src.agents.devils_advocate import critique_thesis

from src.schemas.query import ResearchQuery
from src.schemas.evidence import Evidence, EvidenceLedger
from src.schemas.thesis import Thesis

"""
'''
def test_critique_thesis():
    thesis = Thesis(
        thesis="Apple showed negative short-term returns.",
        supporting_evidence=["total_return", "return_series"],
        contradicting_evidence=[],
        confidence=0.8,
    )

    evidence = EvidenceLedger(items=[])

    result = critique_thesis(thesis, evidence)

    print(result)

    assert result.critique
    assert isinstance(result.challenged_evidence, list)
    assert isinstance(result.missing_evidence, list)
    assert 0.0 <= result.confidence <= 1.0
'''

def test_critique_thesis():
    #iniitial single graph run case(jsut research_planner) used

    research_query = ResearchQuery(
        original_query="Analyze Apple's valuation.",
        task_types=["financial_analysis"],
    )

    evidence_plan = EvidenceLedger(
        items=[
            Evidence(
                claim="AAPL has a reported valuation metric.",
                source_type="financial_data",
                source="financial_metrics",
                evidence="trailingPE = 37.8.",
                confidence=0.95,
                status="SUPPORTED",
            )
        ]
    )

    thesis = Thesis(
        thesis="Apple's valuation was assessed using financial metrics.",
        supporting_evidence=[
            "trailingPE = 37.8."
        ],
        confidence=0.5,
    )

    critique_plan = critique_thesis(
        thesis=thesis,
        evidence=evidence_plan,
        research_query=research_query,
    )

    print(f"planned case unsuccessful run, result:")
    print(critique_plan)

    #double graph run case/replanned scope case:-
    evidence_replan = EvidenceLedger(
        items=[
                Evidence(
                    claim="AAPL has a reported valuation metric.",
                    source_type="financial_data",
                    source="financial_metrics",
                    evidence="trailingPE = 37.8.",
                    confidence=0.95,
                    status="SUPPORTED",
                ),
                Evidence(
                    claim="External research provides evidence relevant to Apple's valuation.",
                    source_type="external_research",
                    source="https://example.com/apple-valuation",
                    evidence="External research provides context on Apple's valuation.",
                    confidence=0.80,
                    status="SUPPORTED",
                )
            ]
        )

    critique_replan = critique_thesis(
        thesis=thesis,
        evidence=evidence_replan,
        research_query=research_query,
    )

    print(f"plan-->replan case successful run, result:")
    print(critique_replan)

    


if __name__ == "__main__":
    test_critique_thesis()
"""
import json
from unittest.mock import Mock, patch

from src.agents.devils_advocate import _generate_critique


def test_generate_critique_valid_response():
    thesis = Mock()
    thesis.model_dump.return_value = {"thesis": "AAPL shows growth."}

    evidence = Mock()
    evidence.items = []

    response = Mock()
    response.content = json.dumps({
        "critique": "The thesis lacks comparative evidence.",
        "confidence": 0.72,
    })

    with patch(
        "src.agents.devils_advocate.invoke_with_fallback",
        return_value=response,
    ) as mock_llm:
        critique, confidence = _generate_critique(
            thesis=thesis,
            evidence=evidence,
            challenged_evidence=["Low-confidence evidence: AAPL growth."],
            missing_evidence=["Missing market evidence."],
            fallback_critique="Fallback critique.",
            fallback_confidence=0.6,
        )

    assert critique == "The thesis lacks comparative evidence."
    assert confidence == 0.72
    mock_llm.assert_called_once()


def test_generate_critique_invalid_json_falls_back():
    thesis = Mock()
    thesis.model_dump.return_value = {"thesis": "AAPL shows growth."}

    evidence = Mock()
    evidence.items = []

    response = Mock()
    response.content = "not valid JSON"

    with patch(
        "src.agents.devils_advocate.invoke_with_fallback",
        return_value=response,
    ):
        critique, confidence = _generate_critique(
            thesis, evidence, [], [],
            "Fallback critique.", 0.6,
        )

    assert critique == "Fallback critique."
    assert confidence == 0.6


def test_generate_critique_llm_exception_falls_back():
    thesis = Mock()
    thesis.model_dump.return_value = {"thesis": "AAPL shows growth."}

    evidence = Mock()
    evidence.items = []

    with patch(
        "src.agents.devils_advocate.invoke_with_fallback",
        side_effect=RuntimeError("LLM unavailable"),
    ):
        critique, confidence = _generate_critique(
            thesis, evidence, [], [],
            "Fallback critique.", 0.6,
        )

    assert critique == "Fallback critique."
    assert confidence == 0.6


def test_generate_critique_rejects_out_of_range_confidence():
    thesis = Mock()
    thesis.model_dump.return_value = {"thesis": "AAPL shows growth."}

    evidence = Mock()
    evidence.items = []

    response = Mock()
    response.content = json.dumps({
        "critique": "Insufficient evidence.",
        "confidence": 1.5,
    })

    with patch(
        "src.agents.devils_advocate.invoke_with_fallback",
        return_value=response,
    ):
        critique, confidence = _generate_critique(
            thesis, evidence, [], [],
            "Fallback critique.", 0.6,
        )

    assert critique == "Fallback critique."
    assert confidence == 0.6