import asyncio

from datetime import date

from src.graph.state import QuantPilotState
from src.graph.workflow import research_executor_node
from src.schemas.research import ResearchPlan, ResearchStep


def test_plan_replan_research_executor():
    #we need to check reserach_plan and replan_plan one at a time
    
    '''
    research_plan = ResearchPlan(
        query="Compare Apple's valuation, and market trend.",
        research_questions=[
            "How does Apple's valuation compare to historical levels?",
            "What are Apple's recent market trends?",
        ],
        steps=[
            ResearchStep(
                step_id=1,
                task_type="comparison",
                tool_category="research",
                objective="Collect external research on Apple's valuation and market trends.",
                required=True,
            ),
        ],
    )
    '''

    
    replan_plan = ResearchPlan(
        query="Compare Apple's valuation, and market trend.",
        research_questions=[
            "How does Apple's valuation compare to historical levels?",
            "What are Apple's recent market trends?",
        ],
        steps=[
            ResearchStep(
                step_id=2,
                task_type="market_analysis",
                tool_category="research",
                objective="Gather additional external market research.",
                required=True,
            ),
            ResearchStep(
                step_id=4,
                task_type="financial_analysis",
                tool_category="research",
                objective="Gather additional external financial research.",
                required=True,
            ),
        ],
    )

    

    initial_state: QuantPilotState = {
        "user_query": "Compare Apple's valuation, and market trend.",
        "ticker": "AAPL",
        "start": date(2025, 1, 1),
        "end": date(2025, 1, 8),
        #"research_plan": research_plan,#when executing research_plan only
        "replan_plan": replan_plan,#when executing replan_plan only
        "replan_financial_metrics": ["market"],
        "research_results": [],
        "replan_count":1#when executing replan_plan only
    }

    result = asyncio.run(research_executor_node(initial_state))

    print("\nResearch Executor output:")
    print(result)

    assert "research_results" in result
    assert result["research_results"]