from datetime import date

from src.agents.query_analyzer import analyze_query
from src.agents.research_planner import create_research_plan
from src.agents.replan_researcher import replan_research
from src.agents.research_executor import execute_research_plan
from src.schemas.adjudication import Adjudication
from src.schemas.evidence import Evidence, EvidenceLedger

import asyncio

# Incremental tests for the new research-result synthesis helper.

import pytest
from types import SimpleNamespace
from unittest.mock import patch

from src.agents.research_executor import enhance_research_result





'''
def main():
    research_query = analyze_query(
        "Analyze Apple's historical volatility."
    )

    research_plan = create_research_plan(research_query)

    execution_sequence = execute_research_plan(research_plan)

    for step in execution_sequence:
        print(step)

'''

'''
async def main():
    research_query = analyze_query(
        "Analyze Apple's historical volatility."
    )

    research_plan = create_research_plan(research_query)

    results = await execute_research_plan(
        research_plan=research_plan,
        ticker="AAPL",
        start=date(2025, 1, 1),
        end=date(2026, 1, 1),
    )

    for result in results:
        print(result)
'''

# ============================================================
# EXISTING MANUAL TEST / DEMONSTRATION
# ============================================================

"""
async def main() -> None:
    

    ticker = "AAPL"
    start = date(2025, 1, 1)
    end = date(2025, 1, 8)
    financial_metrics = ["trailingPE", "marketCap"]

    # --------------------------------------------------
    # 1. Initial plan -> initial execution
    # --------------------------------------------------

    #1st iter:- query for task_type='qunatitauive _analysis' forcefully feeded for both plan 
    # and replan o/p check(techincally not needed as no incremental o/p in replan, neither yeilding 
    # relevant missing evidences in 1st run adjuidcator, but somehgow forced for our demo)
    #2nd iter:- query for task_type='financial_analyis'--->gives logical flow
    #3rd iter:- for non-fionancial_tanalysis task(currenty task type:- 'market_analysis') 
    # which doesn't have finnacial_metric to begin, but get dynamic financial_metric list generated 
    # in replan o/p (after lookup from Yfinace_info_lookup corpus)
    #4th iter:- for non-fionancial_tanalysis task(currenty task type:- 'quantitaive_analysis')
    #after updating replan_tool-task map(adding 'financial' tool_cat for given task type).
    #5th iter:-testing compound cases(financial_analysis+qunatotaive_analysis+market_analysis). 
    # Particularly check whether tool_cat='finacial' in replan run for last 2 tasks given
    #dynamic financial_metric cretaed from YF_info list lookup for query and chnage in missing 
    #evidence:- now both task_types and tool_category.

    research_query = analyze_query(
        #"Analyze Apple's historical volatility."
        #"Analyze Apple's valuation.",
        #"Analyze Apple's fiftyDayAverage."
        #"Analyze appel's beta."#4th iter.
        "Compare Apple's returns, valuation, and market trend."#compound csae(5th iter)
        #"Compare Apple's valuation, and market trend."#compound csae"
        #"Analyze apple's valuation and fiftyDayAverage."

    )

    research_plan = create_research_plan(research_query)

    print("\nINITIAL PLAN")
    print(research_plan)

    initial_results = await execute_research_plan(
        research_plan=research_plan,
        ticker=ticker,
        start=start,
        end=end,
        financial_metrics=financial_metrics,#commented for 3rd iter
    )

    print("\nINITIAL RESULTS")
    for result in initial_results:
        print(result["tool_category"])

    # --------------------------------------------------
    # 2. Replan -> incremental execution
    # --------------------------------------------------
    
    #for iter1:-task_types->quantitaibve_analysis
    '''
    adjudication = Adjudication(
        decision="FAIL",
        rationale="Additional evidence is required.",
        evidence_debt=[
            "Missing market evidence.",
            "Missing quantitative evidence.",
        ],
        confidence=0.6,
    )
    '''

    '''
    #for iter2:-task_types->financial_analysis
    adjudication = Adjudication(
        decision="FAIL",
        rationale="Additional financial evidence is required.",
        evidence_debt=[
            "Missing research evidence."
        ],
        confidence=0.6,
    )
    '''

    '''
    #for iter3:-task_types->market_analysis==>dynamic finance_metrc generated from 
    # query in replan 2nd round
    adjudication = Adjudication(
        decision="FAIL",
        rationale="Additional financial and research evidence is required.",
        evidence_debt=[
            "Missing financial evidence.",
            "Missing research evidence.",
        ],
        confidence=0.6,
    )
    '''

    '''
    #for iter4:-task_types->quantitaive_analysis==>dynamic finance_metrc generated from 
     # query in replan 2nd round(after updating replan_tak-tool map with incremental addn of 
     # 'financial' tool_category)
    adjudication = Adjudication(
        decision="FAIL",
        rationale="Additional financial evidence is required.",
        evidence_debt=[
            "Missing financial evidence.",
        ],
        confidence=0.6,
    )
    '''

    #for iter 5:- compoubd case(M+Q+F analysis task type)-->altered evidence dbt(missing evidence)
    #'finance' tool_cat twice run(plan+replan) after dynamic finance_metrc generation like iter3,4
    adjudication = Adjudication(
        decision="FAIL",
        rationale="Additional evidence is required for the compound analysis.",
        evidence_debt=[
            "Missing research evidence for financial_analysis.",
            "Missing financial evidence for financial_analysis.",
            "Missing financial evidence for quantitative_analysis.",
        ],
        confidence=0.6,
    )

    dummy_evidence = EvidenceLedger(
        items=[
            Evidence(
                claim="Dummy supporting claim",
                source_type="market_data",
                source="historical_prices",
                task_type="market_analysis",
                tool_category="market",
                evidence="Dummy test evidence",
                confidence=0.9,
                status="SUPPORTED",
            )
        ]
    )
    


    replan, replan_financial_metrics = replan_research(
        research_query=research_query,
        evidence = dummy_evidence,
        adjudication=adjudication,
    )

    print("\nREPLAN")
    print(replan)

    print(f"replan_financial_metrics:-{replan_financial_metrics}")

    replan_results = await execute_research_plan(
        research_plan=replan,
        ticker=ticker,
        start=start,
        end=end,
        financial_metrics=financial_metrics,#commented for 3rd iter
        replan_financial_metrics= replan_financial_metrics,
        existing_results=initial_results,
    )

    print("\nREPLAN RESULTS")
    for result in replan_results:
        print(f"tool_category:-{result['tool_category']}")
    
        if(result['tool_category'] =='financial'):
            print(f"result:-{result['result']}")


if __name__ == "__main__":
    asyncio.run(main())
"""

# ============================================================
# ADDITIONAL MOCK TESTS — NEW LLM HELPER FUNCTIONS
# ============================================================


def test_enhance_research_result_adds_synthesized_summary():
    result = {
        "query": "AAPL outlook",
        "sources": [
            {
                "title": "Source 1",
                "url": "https://example.com",
                "content": "Revenue increased.",
            }
        ],
    }

    with patch(
        "src.agents.research_executor.invoke_with_fallback",
        return_value=SimpleNamespace(content="  Revenue increased.  "),
    ) as mock_llm:
        enhanced = enhance_research_result(result)

    assert enhanced["synthesized_summary"] == "Revenue increased."
    assert enhanced["sources"] == result["sources"]
    assert "synthesized_summary" not in result
    mock_llm.assert_called_once()


def test_enhance_research_result_skips_empty_sources():
    result = {"query": "AAPL outlook", "sources": []}

    with patch(
        "src.agents.research_executor.invoke_with_fallback"
    ) as mock_llm:
        assert enhance_research_result(result) is result

    mock_llm.assert_not_called()


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(content=""),
        SimpleNamespace(content="   "),
        SimpleNamespace(content=None),
        SimpleNamespace(content=123),
    ],
)

def test_enhance_research_result_falls_back_on_invalid_summary(response):
    result = {
        "sources": [
            {"title": "Source", "url": "https://example.com", "content": "Text"}
        ]
    }

    with patch(
        "src.agents.research_executor.invoke_with_fallback",
        return_value=response,
    ):
        assert enhance_research_result(result) is result


def test_enhance_research_result_falls_back_on_llm_exception():
    result = {
        "sources": [
            {"title": "Source", "url": "https://example.com", "content": "Text"}
        ]
    }

    with patch(
        "src.agents.research_executor.invoke_with_fallback",
        side_effect=RuntimeError("LLM unavailable"),
    ):
        assert enhance_research_result(result) is result


def test_enhance_research_result_respects_max_chars():
    result = {
        "sources": [
            {"title": "Source", "url": "https://example.com", "content": "Text"}
        ]
    }

    with patch(
        "src.agents.research_executor.invoke_with_fallback",
        return_value=SimpleNamespace(content="A" * 100),
    ):
        enhanced = enhance_research_result(result, max_chars=20)

    assert len(enhanced["synthesized_summary"]) == 20