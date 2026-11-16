from src.schemas.adjudication import Adjudication
from src.schemas.evidence import EvidenceLedger
from src.schemas.thesis import Thesis
from src.schemas.critique import Critique

from typing import Literal, TypeAlias, cast

import json

from langchain_core.messages import HumanMessage, SystemMessage
from src.llm import invoke_with_fallback

import logging
logger = logging.getLogger(__name__)

def _research_quality(
    evidence: EvidenceLedger,
    evidence_debt: list[str],
) -> tuple[float, str]:
    distinct_evidence = {
        (
            item.claim,
            item.source_type,
            item.source,
            item.evidence,
        )
        for item in evidence.items
    }
    distinct_debt = {
        debt.strip().casefold()
        for debt in evidence_debt
        if debt and debt.strip()
    }

    evidence_count = len(distinct_evidence)
    debt_count = len(distinct_debt)

    if evidence_count == 0:
        score = 0.0
    else:
        score = evidence_count / (evidence_count + debt_count)

    if score == 1.0:
        band = "FULLY_PASSED"
    elif score >= 0.8:
        band = "STRONGLY_PASSED"
    elif score >= 0.6:
        band = "FAIRLY_PASSED"
    elif score >= 0.4:
        band = "AVERAGE"
    elif score >= 0.2:
        band = "POOR"
    else:
        band = "FAILED"

    return round(score, 4), band

#LLM rationale/confidence, with validated output and a deterministic fallback.
def _generate_adjudication(
    thesis: Thesis,
    critique: Critique,
    evidence: EvidenceLedger,
    decision: str,
    evidence_debt: list[str],
    fallback_rationale: str,
    fallback_confidence: float,
) -> tuple[str, float]:
    """Generate a validated adjudication rationale and confidence."""

    messages = [
        SystemMessage(
            content=(
                "Act as a rigorous evidence adjudicator in QuantPilot's financial "
                "research workflow. Evaluate the supplied thesis, Devil's Advocate "
                "critique, evidence ledger, predetermined decision, and evidence debt. "
                "Your role is to explain and assess the justification for the supplied "
                "decision, not to independently change or re-evaluate that decision. "
                "Generate an evidence-grounded rationale and calibrated confidence score. "
                "Be honest and evidence-grounded; do not invent facts, "
                "change the supplied decision or evidence_debt, or treat a PASS as proof "
                "that every claim is factually correct. Generate a concise rationale "
                "explaining the decision. Confidence must reflect how reliably the "
                "adjudication is justified by the evidence, not merely the model's "
                "certainty in its wording. Keep the rationale concise, coherent, and "
                "complete regarding material evidence limitations. Treat duplicate copies "
                "of the same underlying evidence as one fact, not independent corroboration. "
                "Return valid JSON in the below format only;"
                '{"rationale":"...", "confidence":0.6}. Do not exceed 512 output tokens. '
                "The example confidence is illustrative; determine it from how well "
                "the supplied evidence justifies the given decision, not from the example. "
                "Confidence must be numeric between 0 and 1."
            )
        ),
        HumanMessage(
            content=json.dumps(
                {
                    "decision": decision,
                    "evidence_debt": evidence_debt,
                    "thesis": thesis.model_dump(),
                    "critique": critique.model_dump(),
                    "evidence": [
                        item.model_dump() for item in evidence.items
                    ],
                },
                ensure_ascii=False,
                default=str,
            )
        ),
    ]

    try:
        response = invoke_with_fallback("judge", messages)

        #print(f"Adjudicator raw response: {response.content!r}")

        if not isinstance(response.content, str):
            raise ValueError("LLM response content must be a string")

        result = json.loads(response.content)
        rationale = result["rationale"]
        confidence = result["confidence"]

        if (
            not isinstance(rationale, str)
            or not rationale.strip()
            or not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("Invalid adjudication response")

        return rationale.strip(), float(confidence)

    except Exception:
            
        logger.exception("Adjudication rationale generation failed; using fallback.")

        return fallback_rationale, fallback_confidence

#main function
def adjudicate_evidence(
    thesis: Thesis,
    critique: Critique,
    evidence: EvidenceLedger,
) -> Adjudication:

    if thesis is None or critique is None or evidence is None:
        raise ValueError(
            "Thesis, critique, and evidence are required for adjudication"
        )

    evidence_debt: list[str] = []

    evidence_count = len(evidence.items)

    if not thesis.supporting_evidence:
        evidence_debt.append("Thesis has no supporting evidence.")

    if critique.missing_evidence:
        evidence_debt.extend(critique.missing_evidence)

    if critique.challenged_evidence:
        evidence_debt.extend(critique.challenged_evidence)

    if evidence_debt:
        decision = "FAIL"
        fallback_rationale = ("The thesis has unresolved evidence limitations.")
        fallback_confidence = 0.6

    elif evidence_count == 0:
        decision = "FAIL"
        fallback_rationale = ("No evidence is available to support the thesis.")
        fallback_confidence = 0.9

    else:
        decision = "PASS"
        fallback_rationale = (
            "The thesis has sufficient supporting evidence with "
            "no identified unresolved limitations.")
        fallback_confidence = 0.8

    quality_score, quality_band = _research_quality(
        evidence, evidence_debt
    )

    rationale, confidence = _generate_adjudication(
        thesis=thesis,
        critique=critique,
        evidence=evidence,
        decision=decision,
        evidence_debt=evidence_debt,
        fallback_rationale=fallback_rationale,
        fallback_confidence=fallback_confidence,
    )

    return Adjudication(
        decision=decision,
        rationale=rationale,
        evidence_debt=evidence_debt,
        confidence=confidence,
        quality_score=quality_score,
        quality_band = cast(
            Literal[
                "FULLY_PASSED", "STRONGLY_PASSED", "FAIRLY_PASSED",
                "AVERAGE", "POOR", "FAILED",
            ],
            quality_band,
        )
    )