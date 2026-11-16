from types import SimpleNamespace

from src.agents import research_planner
from src.schemas.query import ResearchQuery

from src.agents.query_analyzer import analyze_query
from src.agents.research_planner import create_research_plan

'''
def main():
    #single-intent checks
    research_query = analyze_query("Analyze Apple's historical volatility.")

    research_plan = create_research_plan(research_query)

    print(research_query)
    print()
    print(research_plan)

    assert [step.tool_category for step in research_plan.steps] == ["quantitative"]

    #multi-intent checks
    research_query = analyze_query("Compare Apple's returns and valuation.")

    research_plan = create_research_plan(research_query)

    assert [step.tool_category for step in research_plan.steps] == [
        "market",
        "financial",
        "quantitative",
        "research",
    ]


if __name__ == "__main__":
    main()
'''

def make_query():
    return ResearchQuery(
        original_query="Compare Apple's returns and valuation.",
        task_types=["comparison"],
        entities=["Apple", "AAPL"],
        research_questions=["How did Apple's returns compare with its valuation?"],
        metrics=["returns", "valuation"],
    )


def test_refine_objective_uses_llm_output(monkeypatch):
    monkeypatch.setattr(
        research_planner,
        "invoke_with_fallback",
        lambda *args, **kwargs: SimpleNamespace(
            content="Compare historical price movements with relevant valuation metrics."
        ),
    )

    objective = research_planner.refine_objective(make_query(), "market")

    assert objective == (
        "Compare historical price movements with relevant valuation metrics."
    )


def test_refine_objective_falls_back_on_empty_output(monkeypatch):
    monkeypatch.setattr(
        research_planner,
        "invoke_with_fallback",
        lambda *args, **kwargs: SimpleNamespace(content="  "),
    )

    objective = research_planner.refine_objective(make_query(), "market")

    assert objective == research_planner.TOOL_OBJECTIVES["market"]


def test_refine_objective_falls_back_on_invalid_output(monkeypatch):
    monkeypatch.setattr(
        research_planner,
        "invoke_with_fallback",
        lambda *args, **kwargs: SimpleNamespace(content={"objective": "Use market data"}),
    )

    objective = research_planner.refine_objective(make_query(), "market")

    assert objective == research_planner.TOOL_OBJECTIVES["market"]


def test_refine_objective_falls_back_when_gateway_raises(monkeypatch):
    def fail_gateway(*args, **kwargs):
        raise RuntimeError("Simulated provider failure")

    monkeypatch.setattr(research_planner, "invoke_with_fallback", fail_gateway)

    objective = research_planner.refine_objective(make_query(), "market")

    assert objective == research_planner.TOOL_OBJECTIVES["market"]


def test_create_research_plan_preserves_tool_selection(monkeypatch):
    # Isolate deterministic planning from LLM objective refinement.
    monkeypatch.setattr(
        research_planner,
        "refine_objective",
        lambda query, category: f"Refined {category} objective",
    )

    plan = research_planner.create_research_plan(make_query())

    assert [step.tool_category for step in plan.steps] == [
        "market",
        "financial",
        "quantitative",
        "research",
    ]
    assert all(step.objective.startswith("Refined ") for step in plan.steps)
    assert plan.query == make_query().original_query