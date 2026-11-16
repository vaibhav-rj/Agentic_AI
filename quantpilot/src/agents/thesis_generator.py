import json

from langchain_core.messages import SystemMessage, HumanMessage

from src.schemas.thesis import Thesis
from src.schemas.evidence import EvidenceLedger
from src.llm import invoke_with_fallback

import logging

logger = logging.getLogger(__name__)

def generate_thesis(
    user_query: str,
    evidence: EvidenceLedger,
) -> Thesis:
    '''
    supporting = [
        item.evidence
        for item in evidence.items
        if item.status == "SUPPORTED"
    ]

    contradicting = [
        item.evidence
        for item in evidence.items
        if item.status in {"CONFLICTING", "UNSUPPORTED"}
    ]
    '''
    supporting = list(dict.fromkeys(
        item.evidence
        for item in evidence.items
        if item.status == "SUPPORTED"
    ))

    contradicting = list(dict.fromkeys(
        item.evidence
        for item in evidence.items
        if item.status in {"CONFLICTING", "UNSUPPORTED"}
    ))

    fallback_thesis = f"Research findings were collected for: {user_query}"

    if not evidence.items:
        return Thesis(
            thesis=fallback_thesis,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            confidence=0.5,
        )

    prompt_data = [
        {
            "claim": item.claim,
            "status": item.status,
            "confidence": item.confidence,
            "evidence": item.evidence,
            "source": item.source,
        }
        for item in evidence.items
    ]

    messages = [
        SystemMessage(
            content=(
                 "Generate a concise thesis answering user_query using only the "
                "supplied evidence. Be strict and honest: do not invent facts, "
                "introduce unsupported comparisons, or infer market performance "
                "without comparative data. Distinguish measured facts from "
                "inferences and acknowledge material evidence gaps or conflicts. "
                "The Thesis object contains thesis, supporting_evidence, "
                "contradicting_evidence, and confidence. Generate only thesis and "
                "overall confidence as JSON; Python derives the evidence lists from "
                "EvidenceLedger statuses. Confidence must reflect how strongly the "
                "combined evidence supports the entire thesis, not individual item "
                "confidence or evidence quantity."
                "Treat duplicate copies of the same underlying evidence as one "
                "fact, not independent corroboration. Keep the thesis concise, coherent "
                "but complete regarding material evidence gaps or conflicts. "
                "Return valid JSON in the below format only;"
                '{"thesis":"...", "confidence":0.75}. Do not exceed 512 output tokens.'
                "The example values are illustrative; determine thesis and confidence "
                "from the actual combined evidence, without copying the example confidence."
                "Confidence must be numeric and between 0 and 1."
            )
        ),
        HumanMessage(
            content=json.dumps(
                {
                    "user_query": user_query,
                    "evidence": prompt_data,
                },
                ensure_ascii=False,
            )
        ),
    ]

    try:
        response = invoke_with_fallback("judge", messages)
        content = response.content

        #print(f"Thesis raw response: {content!r}")

        if not isinstance(content, str):
            raise ValueError("LLM response content is not a string")

        result = json.loads(content)
        thesis_text = result["thesis"]
        confidence = result["confidence"]

        if (
            not isinstance(thesis_text, str)
            or not thesis_text.strip()
            or not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("Invalid thesis response")

        return Thesis(
            thesis=thesis_text.strip(),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            confidence=float(confidence),
        )

    except Exception:
        logger.exception(
            "Thesis generation failed; using fallback thesis."
        )
        return Thesis(
            thesis=fallback_thesis,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            confidence=0.5,
        )    