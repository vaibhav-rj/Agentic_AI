from src.schemas.evidence import Evidence, EvidenceLedger

import json
import hashlib

from langchain_core.messages import SystemMessage, HumanMessage
from src.llm import invoke_with_fallback

import logging

logger = logging.getLogger(__name__)

def _assessment_key(item: Evidence) -> str:
    payload = {
        "claim": item.claim,
        "source_type": item.source_type,
        "source": item.source,
        "evidence": item.evidence,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def assess_evidence_ledger(
    ledger: EvidenceLedger,
    previously_assessed: EvidenceLedger | None = None,
) -> EvidenceLedger:
    if not ledger.items:
        return ledger

    assessment_cache = {
        _assessment_key(item): item
        for item in (previously_assessed.items if previously_assessed else [])
    }
    #print(assessment_cache)

    items = []
    allowed_statuses = {
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "UNSUPPORTED",
        "CONFLICTING",
        "UNVERIFIED",
    }

    current_unique_key={}

    for i, item in enumerate(ledger.items):
        #print(f"task_types:{item.task_type}{'-'*20}\ntool_category:{item.tool_category}{'-'*20}\nsource:{item.source}"\
        #f"{'-'*20}\nevidence:{item.evidence}{'-'*20}")

        item_key = _assessment_key(item)
        cached_item = assessment_cache.get(item_key)
        print(cached_item)

        if cached_item is not None:

            items.append(
                item.model_copy(
                    update={
                        "confidence": cached_item.confidence,
                        "status": cached_item.status,
                    }
                )
            )
            continue
        
        else:
            key =  _assessment_key(item)
            if key in current_unique_key:
                items.append(
                    item.model_copy(
                        update={

                            "confidence": current_unique_key[key][1],
                            "status": current_unique_key[key][0]  
                        }
                    )
                )
                continue
            
            else:
                messages = [
                    SystemMessage(
                        content=(
                            "Assess whether the supplied evidence supports its claim. "
                            "Judge each item independently; do not rely on other research "
                            "steps or evidence items. Be strict and honest: distinguish "
                            "direct support from partial, weak, irrelevant, contradictory, "
                            "or insufficient evidence. Assign an item-specific confidence "
                            "score reflecting actual evidence quality; do not default to "
                            "0.9 or force variation when evidence quality is similar. "
                            "Evaluate external research for contextual relevance and source "
                            "reliability, without automatically penalizing or trusting it. "
                            "Return valid JSON in below format only: "
                            '{"status":"SUPPORTED","confidence":0.9}. '
                            "Choose the status and confidence independently for each item "
                            "based on its actual evidence; do not default to the example values."
                            "Allowed statuses: SUPPORTED, PARTIALLY_SUPPORTED, "
                            "UNSUPPORTED, CONFLICTING, UNVERIFIED. "
                            "Confidence must be between 0 and 1."
                        )
                    ),
                    HumanMessage(
                        content=json.dumps(
                            {
                                "claim": item.claim,
                                "source_type": item.source_type,
                                "source": item.source,
                                "evidence": item.evidence,
                            },
                            ensure_ascii=False,
                        )
                    ),
                ]

                try:
                    response = invoke_with_fallback("judge", messages)
                    content = response.content

                    if not isinstance(content, str):
                        raise ValueError("Response content is not text.")

                    #print(f"repr(contnet)-->{repr(content)}")
                    

                    assessment = json.loads(content)

                    if not isinstance(assessment, dict):
                        raise ValueError("Assessment is not a JSON object.")

                    status = assessment.get("status")
                    confidence = assessment.get("confidence")

                    if (
                        status not in allowed_statuses
                        or not isinstance(confidence, (int, float))
                        or isinstance(confidence, bool)
                        or not 0 <= confidence <= 1
                    ):
                        raise ValueError("Invalid assessment status or confidence.")

                    items.append(
                        item.model_copy(
                            update={
                                "status": status,
                                "confidence": float(confidence),
                            }
                        )
                    )

                except Exception:
                    logger.exception(
                        "Evidence assessment failed for item %d; retaining original item.",
                        i,
                    )
                    items.append(item)

                current_unique_key[key] =(items[-1].status, items[-1].confidence)

    return EvidenceLedger(items=items)

'''post reasearch_exceutor o/p'''
def build_evidence_ledger(
    research_results: list[dict],
    previous_evidence: EvidenceLedger | None = None,
) -> EvidenceLedger:
    items: list[Evidence] = []


    for result in research_results:
        category = result["tool_category"]
        data = result["result"]

        #if(data.get('skipped', False)): continue#skipped:-True(means no tool ops)
        if(data== None):
            continue

        if category == "market":
            items.append(
                Evidence(
                    claim=f"{data['ticker']} historical price data was collected.",
                    source_type="market_data",
                    source="historical_prices",
                    task_type=result["task_type"],
                    tool_category=result["tool_category"],
                    step_id=result.get("step_id"),
                    evidence=f"{len(data['bars'])} price observations were collected.",
                    confidence=0.99,
                    status="SUPPORTED",
                )
            )

        elif category == "financial":
            for metric in data["metrics"]:
                if metric["value"] is not None:
                    items.append(
                        Evidence(
                            claim=f"{data['ticker']} has a reported {metric['name']} value.",
                            source_type="financial_data",
                            source="financial_metrics",
                            task_type=result["task_type"],
                            tool_category=result["tool_category"],
                            step_id=result.get("step_id"),
                            evidence=f"{metric['name']} = {metric['value']}.",
                            confidence=0.95,
                            status="SUPPORTED",
                        )
                    )

        elif category == "quantitative":
            total_return = data["total_return"]
            volatility = data["volatility"]
            drawdown = data["max_drawdown"]

            ticker = total_return["ticker"]

            items.extend(
                [
                    Evidence(
                        claim=f"{ticker} had a measured total return over the analyzed period.",
                        source_type="quantitative_analysis",
                        source="total_return",
                        task_type=result["task_type"],
                        tool_category=result["tool_category"],
                        step_id=result.get("step_id"),
                        evidence=f"Total return = {total_return['total_return']:.4%}.",
                        confidence=0.99,
                        status="SUPPORTED",
                    ),
                    Evidence(
                        claim=(
                            f"{total_return['ticker']} had a measured return series "
                            "over the analyzed period."
                        ),
                        source_type="quantitative_analysis",
                        source="return_series",
                        task_type=result["task_type"],
                        tool_category=result["tool_category"],
                        step_id=result.get("step_id"),
                        evidence=(
                            f"{len(data['return_series']['returns'])} return observations "
                            "were measured."
                        ),
                        confidence=0.99,
                        status="SUPPORTED",
                    ),
                    Evidence(
                        claim=f"{ticker} had a measured annualized volatility over the analyzed period.",
                        source_type="quantitative_analysis",
                        source="volatility",
                        task_type=result["task_type"],
                        tool_category=result["tool_category"],
                        step_id=result.get("step_id"),
                        evidence=(
                            f"Annualized volatility = "
                            f"{volatility['annualized_volatility']:.4%}."
                        ),
                        confidence=0.99,
                        status="SUPPORTED",
                    ),
                    Evidence(
                        claim=f"{ticker} had a measured maximum drawdown over the analyzed period.",
                        source_type="quantitative_analysis",
                        source="max_drawdown",
                        task_type=result["task_type"],
                        tool_category=result["tool_category"],
                        step_id=result.get("step_id"),
                        evidence=(
                            f"Maximum drawdown = "
                            f"{drawdown['max_drawdown']:.4%}."
                        ),
                        confidence=0.99,
                        status="SUPPORTED",
                    ),
                ]
            )

        elif category == "research":
            for source in data["sources"]:
                items.append(
                    Evidence(
                        #claim=f"External research provides evidence relevant to '{data['query']}'.",
                        claim=f"External research returned a source for the query: '{data['query']}'.",
                        source_type="external_research",
                        source=source["url"],
                        task_type=result["task_type"],
                        tool_category=result["tool_category"],
                        step_id=result.get("step_id"),
                        evidence=(data.get("synthesized_summary") or source.get("content", "")),
                        confidence=0.80,
                        status="SUPPORTED",
                    )
                )



    return assess_evidence_ledger(
        EvidenceLedger(items=items),
        previously_assessed=previous_evidence,
    )