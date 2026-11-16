from src.schemas.query import ResearchQuery
from src.schemas.research import ResearchPlan, ResearchStep

from typing import Literal, TypeAlias, cast

from src.llm import invoke_with_fallback

from langchain_core.messages import SystemMessage, HumanMessage

import logging

logger =logging.getLogger(__name__)

ToolCategory: TypeAlias = Literal[
    "market",
    "financial",
    "quantitative",
    "research",
]

#earlier values in set for below mapping(as sets don't guarentee odereing)
TASK_TO_TOOLS = {
    "market_analysis": ["market"],
    "financial_analysis": ["financial"],
    "quantitative_analysis": ["market", "quantitative"],
    "comparison": ["market", "financial", "quantitative", "research"],
    "mixed": ["market", "financial", "quantitative", "research"],
}


TOOL_OBJECTIVES = {
    "market": "Collect relevant historical market price data.",
    "financial": "Collect relevant company financial metrics.",
    "quantitative": "Perform the quantitative analysis required by the query.",
    "research": "Gather supporting external evidence and context.",
}

# Refine objectives using query context without changing deterministic tool selection.
def refine_objective(
    research_query: ResearchQuery,
    tool_category: ToolCategory,
) -> str:
    """Refine an existing objective without changing tool selection."""
    default_objective = TOOL_OBJECTIVES[tool_category]

    messages = [
        SystemMessage(content="""
    You refine research objectives.

    Refine the research objective for a financial research workflow.

    Rules:-
    1) Use the relevant task type, research questions, entities, and tool category
    to produce a concise, actionable, query-specific objective.
    2) Preserve the default objective's intent and remain within the tool category's scope.
    3) Do not propose other tools, invent data, or change the requested task.
    4) Each generated objective in step1 should be specific & unique, to the given configuration:
    - mainly governed by uniqueness of task type & tool category couple.
    - although should also reflect the common original query, research questions, entities, tool category.
    - It should be just incremental improvement to default objective keeping configurational context in account.
    5) The generated objective should be one(not multiple), complete, compact yet concise.

    Return only the objective text. Return plain text only.
    """),
        HumanMessage(content=f"""
    Original query: {research_query.original_query}
    Research questions: {research_query.research_questions}
    Entities: {research_query.entities}
    Tool category: {tool_category}
    Default objective: {default_objective}
    Task types: {research_query.task_types}
    """)
    ]



    try:
        response = invoke_with_fallback("reasoning", messages)
        
        content = response.content
        #print(f"content(repr):-{content}")
        logger.debug("Research objective refinement response received")

        if not isinstance(content, str):
            return default_objective

        objective = content.strip()
        if (
            not objective
            or len(objective) > 500
            or objective.startswith("{")
        ):
            return default_objective# Preserve a reliable deterministic objective if LLM refinement fails.

        return objective

    except Exception:
        logger.warning("Objective refinement failed; using default objective", exc_info=True)
        return default_objective

def create_research_plan(
    research_query: ResearchQuery,
) -> ResearchPlan:
    """Create a research plan from the detected task types."""

    '''
    tool_categories = set()

    for task_type in research_query.task_types:
        mapped_tools = TASK_TO_TOOLS.get(task_type)

        if mapped_tools:
            tool_categories.update(mapped_tools)

    steps: list[ResearchStep] = []
    step_id = 1

    for tool_category in TOOL_ORDER:
        if tool_category in tool_categories:
            steps.append(
                ResearchStep(
                    step_id=step_id,
                    tool_category= cast(ToolCategory, tool_category),#need to csat string to type ToolCategory
                    objective=TOOL_OBJECTIVES[tool_category],
                )
            )
            step_id += 1

    '''
    steps: list[ResearchStep] = []
    step_id = 1

    for task_type in research_query.task_types:
        for tool_category in TASK_TO_TOOLS.get(task_type, []):
            steps.append(
                ResearchStep(
                    step_id=step_id,
                    task_type=task_type,
                    tool_category=cast(ToolCategory, tool_category),
                    #objective=refine_objective(research_query, cast(ToolCategory, tool_category)),
                    objective=TOOL_OBJECTIVES[tool_category],
                    # Keep existing steps and task associations; customize only each objective.
                )
            )
            step_id += 1

    logger.info("Research plan created | steps=%d | task_types=%s", len(steps), research_query.task_types)

    return ResearchPlan(
        query=research_query.original_query,
        steps=steps,
        research_questions=research_query.research_questions
    )