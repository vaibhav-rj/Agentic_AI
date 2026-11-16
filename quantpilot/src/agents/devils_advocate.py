from src.schemas.critique import Critique
from src.schemas.evidence import EvidenceLedger
from src.schemas.thesis import Thesis

from src.schemas.query import ResearchQuery

from src.agents.research_planner import TASK_TO_TOOLS
from src.agents.replan_researcher import REPLAN_TASK_TO_TOOLS

import json

from langchain_core.messages import SystemMessage, HumanMessage
from src.llm import invoke_with_fallback

import logging

logger = logging.getLogger(__name__)

MAX_REPLANS=1

#to obtain the critique text and confidence
def _generate_critique(
    thesis: Thesis,
    evidence: EvidenceLedger,
    challenged_evidence: list[str],
    missing_evidence: list[str],
    fallback_critique: str,
    fallback_confidence: float,
) -> tuple[str, float]:
    """Generate a validated LLM critique with a deterministic fallback."""
    messages = [
        SystemMessage(
            content=(
                "Act as a rigorous Devil's Advocate in a financial research workflow. "
                "Critically evaluate the thesis using the supplied thesis, evidence, "
                "and identified missing/challenged evidence. Assess evidence quality, "
                "relevance, coverage, unresolved conflicts, and whether the thesis's "
                "confidence is justified. Be strict and honest: identify material "
                "weaknesses and unsupported inferences without inventing facts or "
                "changing the supplied evidence classifications or lists. Distinguish "
                "claims supported only by synthesized external research from those "
                "corroborated by structured market, financial, or quantitative evidence; "
                "assess their relevance, reliability, and independent corroboration. "
                "Treat duplicate copies of the same underlying evidence as one fact, "
                "not independent corroboration." 
                
                "Keep the critique concise, coherent, "
                "covering only distinct top 3-5 material weaknesses and evidence limitations. "
                "Remove redundant or repetitive or vague observations."
                "Return valid JSON only in the below format only; "
                '{"critique":"...", "confidence":0.6}.  Do not exceed 512 output tokens strictly'
                "(output to be well within that range given other conditions mentioned above)."
                "The example confidence is illustrative; assess the actual thesis "
                "and evidence independently rather than copying that value. "
                "Confidence must reflect how reliably this critique evaluates the "
                "thesis's evidential strength, not the thesis's own confidence or "
                "the model's confidence in its wording. It must be numeric between "
                "0 and 1."  
            )
        ),
        HumanMessage(
            content=json.dumps(
                {
                    "thesis": thesis.model_dump(),
                    "evidence": [
                        {
                            "claim": item.claim,
                            "status": item.status,
                            "confidence": item.confidence,
                            "evidence": item.evidence,
                        }
                        for item in evidence.items
                    ],
                    "missing_evidence": missing_evidence,
                    "challenged_evidence": challenged_evidence,
                },
                ensure_ascii=False,
            )
        ),
    ]

    try:
        response = invoke_with_fallback("judge", messages)
        #print(f"Devil's Advocate raw response: {response.content!r}")

        if not isinstance(response.content, str):
            raise ValueError("LLM response content must be a string")

        result = json.loads(response.content)
        critique_text = result["critique"]
        confidence = result["confidence"]

        if (
            not isinstance(critique_text, str)
            or not critique_text.strip()
            or not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0.0 <= confidence <= 1.0
        ):
            raise ValueError("Invalid critique response")

        return critique_text.strip(), float(confidence)

    except Exception:
        logger.exception("Devil's Advocate generation failed; using deterministic fallback.")

        return fallback_critique, fallback_confidence


#main devils advocate function
def critique_thesis(
    thesis: Thesis,
    evidence: EvidenceLedger,
    research_query: ResearchQuery,
    replan_count: int=0,
    replan_financial_metrics:list[str] | None = None,
) -> Critique:
    
    challenged_evidence: list[str] = []
    missing_evidence: list[str] = []

    

    #missing evidence codeblock
    if not thesis.supporting_evidence:
        missing_evidence.append("No supporting evidence was provided.")
        
    '''
    required_sources = {
        "market_data": "market",
        "financial_data": "financial",
        "quantitative_analysis": "quantitative",
        "external_research": "research",
    }

    present_sources = {item.source_type for item in evidence.items}

    for source_type, tool_category in required_sources.items():
        if source_type not in present_sources:
            missing_evidence.append(
                f"Missing {tool_category} evidence."
            )
    '''
    tool_to_source = {
        "market": "market_data",
        "financial": "financial_data",
        "quantitative": "quantitative_analysis",
        "research": "external_research",
    }

    #old logic:-agrregating missing tools by subtracting ste of tool union(1st plan run) 
    #from consolidated set tool union of 2nd (replanned run).genratiung missing evidence 
    # from just tool_category.
    ''' 
    required_tools: set[str] = set()

    for task_type in research_query.task_types:
        required_tools.update(
            REPLAN_TASK_TO_TOOLS.get(task_type, set())
        )

    present_sources = {item.source_type for item in evidence.items}

    for tool_category in required_tools:
        source_type = tool_to_source[tool_category]

        if source_type not in present_sources:
            missing_evidence.append(
                f"Missing {tool_category} evidence."
            )
    '''
    #new logic:- mapping the left over icremental tool (replan-plan) task-to-tool mapping for each
    #tsk and generating missing eveidnce from both task_types and tool_category:-
    present_task_tools = {
        (item.task_type, item.tool_category)
        for item in evidence.items
    }

    for task_type in research_query.task_types:
        for tool_category in REPLAN_TASK_TO_TOOLS.get(task_type, set()):

            if (task_type, tool_category) not in present_task_tools:

                if(replan_count==1 and not replan_financial_metrics and tool_category =='financial'):
                #to bypass cases where increne=mental tool_cat was 'financial'(from replan_task_to_tool) but could not be 
                # implemented due to empty dynamic/replan_financial_metrics
                    continue
                
                missing_evidence.append(
                    f"Missing {tool_category} evidence for {task_type}."
                )

            #to help advance task_type:-'finnacial_analysis' for incremental too_cat:-'financial'
            #to handle dyna,ic finn=acial metrics genarted from query
            elif( (task_type =='financial_analysis' and tool_category =='financial') and 
                 (replan_count < MAX_REPLANS) ):

                missing_evidence.append(
                    f"Missing {tool_category} evidence for {task_type}."
                )
            

    #challenged_evidence codeblock

    for item in evidence.items:
        if item.status == "UNSUPPORTED":
            challenged_evidence.append(
                f"Unsupported evidence: {item.claim}"
            )
        elif item.status == "PARTIALLY_SUPPORTED":
            challenged_evidence.append(
                f"Partially supported evidence: {item.claim}"
            )
        elif item.status == "CONFLICTING":
            challenged_evidence.append(
                f"Conflicting evidence: {item.claim}"
            )
        elif item.status == "UNVERIFIED":
            challenged_evidence.append(
                f"Unverified evidence: {item.claim}"
            )

        if item.confidence < 0.7:
            challenged_evidence.append(
                f"Low-confidence evidence: {item.claim}"
            )

    if thesis.confidence >= 0.8 and len(thesis.supporting_evidence) < 2:
        challenged_evidence.append(
            "Thesis confidence may be too high for the amount of supporting evidence."
        )

    challenged_evidence = list(dict.fromkeys(challenged_evidence))

    fallback_critique = (
        "The thesis is supported by the available evidence."
        if not challenged_evidence and not missing_evidence
        else "The thesis should be reviewed against the identified evidence limitations."
    )
    fallback_confidence = 0.8 if not challenged_evidence else 0.6

    critique_text, confidence = _generate_critique(
        thesis=thesis,
        evidence=evidence,
        challenged_evidence=challenged_evidence,
        missing_evidence=missing_evidence,
        fallback_critique=fallback_critique,
        fallback_confidence=fallback_confidence,
    )

    return Critique(
        critique=critique_text,
        challenged_evidence=challenged_evidence,
        missing_evidence=missing_evidence,
        confidence=confidence,
    )