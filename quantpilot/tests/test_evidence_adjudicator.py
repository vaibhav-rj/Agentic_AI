from src.agents.evidence_adjudicator import adjudicate_evidence
from src.schemas.adjudication import Adjudication
from src.schemas.critique import Critique
from src.schemas.evidence import Evidence, EvidenceLedger
from src.schemas.thesis import Thesis

import json
from unittest.mock import Mock, patch

from src.agents.evidence_adjudicator import _generate_adjudication


"""
def test_adjudicate_evidence_pass():
    thesis = Thesis(
        thesis="Apple showed negative short-term returns.",
        supporting_evidence=["total_return", "return_series"],
        confidence=0.8,
    )

    critique = Critique(
        critique="The thesis is supported by the available evidence.",
        challenged_evidence=[],
        missing_evidence=[],
        confidence=0.8,
    )

    # PASS
    evidence = EvidenceLedger(
        items=[
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
                evidence="trailingPE = 38.17546.",
                confidence=0.95,
                status="SUPPORTED",
            ),
        ]
    )
            

    result = adjudicate_evidence(thesis, critique, evidence)

    print(result)

    assert isinstance(result, Adjudication)
    assert result.decision == "PASS"
    assert result.rationale
    assert result.evidence_debt == []
    assert 0.0 <= result.confidence <= 1.0


def test_adjudicate_evidence_fail():
    thesis = Thesis(
        thesis="Apple will outperform the market.",
        supporting_evidence=["market_performance"],
        confidence=0.9,
    )

    critique = Critique(
        critique="The thesis has unresolved evidence limitations.",
        challenged_evidence=["No comparative market evidence."],
        missing_evidence=["Benchmark performance is missing."],
        confidence=0.5,
    )

    # FAIL
    evidence = EvidenceLedger(
        items=[
            Evidence(
                claim="AAPL had a measured total return over the analyzed period.",
                source_type="quantitative_analysis",
                source="total_return",
                evidence="Total return = -0.6725%.",
                confidence=0.99,
                status="SUPPORTED",
            )
        ]
    )
    
    result = adjudicate_evidence(thesis, critique, evidence)

    print(result)

    assert isinstance(result, Adjudication)
    assert result.decision == "FAIL"
    assert result.evidence_debt
    assert 0.0 <= result.confidence <= 1.0


if __name__ == "__main__":
    test_adjudicate_evidence_pass()
    test_adjudicate_evidence_fail()
"""

def _inputs():
    thesis = Mock()
    thesis.model_dump.return_value = {"thesis": "AAPL shows growth."}

    critique = Mock()
    critique.model_dump.return_value = {
        "critique": "Comparative evidence is missing."
    }

    evidence = Mock()
    evidence.items = []

    return thesis, critique, evidence


def test_generate_adjudication_valid_response():
    thesis, critique, evidence = _inputs()
    response = Mock()
    response.content = json.dumps({
        "rationale": "The evidence limitations justify failure.",
        "confidence": 0.91,
    })

    with patch(
        "src.agents.evidence_adjudicator.invoke_with_fallback",
        return_value=response,
    ) as mock_llm:
        rationale, confidence = _generate_adjudication(
            thesis=thesis,
            critique=critique,
            evidence=evidence,
            decision="FAIL",
            evidence_debt=["Missing comparative evidence."],
            fallback_rationale="Fallback rationale.",
            fallback_confidence=0.6,
        )

    assert rationale == "The evidence limitations justify failure."
    assert confidence == 0.91
    mock_llm.assert_called_once()


def test_generate_adjudication_invalid_json_falls_back():
    thesis, critique, evidence = _inputs()
    response = Mock()
    response.content = "invalid JSON"

    with patch(
        "src.agents.evidence_adjudicator.invoke_with_fallback",
        return_value=response,
    ):
        rationale, confidence = _generate_adjudication(
            thesis, critique, evidence,
            "FAIL", ["Missing evidence."],
            "Fallback rationale.", 0.6,
        )

    assert rationale == "Fallback rationale."
    assert confidence == 0.6


def test_generate_adjudication_llm_exception_falls_back():
    thesis, critique, evidence = _inputs()

    with patch(
        "src.agents.evidence_adjudicator.invoke_with_fallback",
        side_effect=RuntimeError("LLM unavailable"),
    ):
        rationale, confidence = _generate_adjudication(
            thesis, critique, evidence,
            "PASS", [],
            "Fallback rationale.", 0.8,
        )

    assert rationale == "Fallback rationale."
    assert confidence == 0.8


def test_generate_adjudication_rejects_invalid_confidence():
    thesis, critique, evidence = _inputs()
    response = Mock()
    response.content = json.dumps({
        "rationale": "The thesis is supported.",
        "confidence": 1.5,
    })

    with patch(
        "src.agents.evidence_adjudicator.invoke_with_fallback",
        return_value=response,
    ):
        rationale, confidence = _generate_adjudication(
            thesis, critique, evidence,
            "PASS", [],
            "Fallback rationale.", 0.8,
        )

    assert rationale == "Fallback rationale."
    assert confidence == 0.8