from datetime import date

from langgraph.graph import END, START, StateGraph

from src.guardrails.input import validate_user_query
from src.guardrails.scope import validate_research_scope

from src.agents.query_analyzer import analyze_query, analyze_query_with_context
from src.agents.research_executor import execute_research_plan
from src.agents.research_planner import create_research_plan
from src.agents.evidence_builder import build_evidence_ledger
from src.agents.thesis_generator import generate_thesis
from src.agents.devils_advocate import critique_thesis
from src.agents.evidence_adjudicator import adjudicate_evidence
from src.agents.final_report import generate_final_report
from src.agents.replan_researcher import replan_research
from src.guardrails.output import validate_final_report

#from src.schemas.final_report import FinalReport

from src.graph.state import QuantPilotState

from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

import logging
import inspect
from functools import wraps
from time import perf_counter

logger = logging.getLogger("quantpilot.workflow")
#from src.guardrails.pii import redact_pii

#new logger chnages for seuqential eval, wrapper preserves the original function's metadata (name, docstring, etc.)
def _logged_async_node(node_name, node_func):
    @wraps(node_func)
    async def wrapper(state):
        started = perf_counter()
        logger.info("Node started: %s", node_name)
        try:
            result = await node_func(state)
            logger.info("Node completed: %s | duration=%.2fs",
                        node_name, perf_counter() - started)
            return result
        except Exception:
            logger.exception("Node failed: %s", node_name)
            raise
    return wrapper


def _logged_sync_node(node_name, node_func):
    @wraps(node_func)
    def wrapper(state):
        started = perf_counter()
        logger.info("Node started: %s", node_name)
        try:
            result = node_func(state)
            logger.info("Node completed: %s | duration=%.2fs",
                        node_name, perf_counter() - started)
            return result
        except Exception:
            logger.exception("Node failed: %s", node_name)
            raise
    return wrapper


def _logged_node(node_name, node_func):
    wrapper = (
        _logged_async_node if inspect.iscoroutinefunction(node_func)
        else _logged_sync_node
    )
    return wrapper(node_name, node_func)#this wrapper either selcets euthe sync or async child wrapper containing node fn 
#(eg:- input_guardrails_node)and clubs it with node_name 

MAX_REPLANS = 1

def input_guardrails_node(state: QuantPilotState) -> dict:

    print(">>> ENTERED input_guardrails_node", flush=True)

    """Validate query length and research scope before LLM processing."""
    query = validate_user_query(state["user_query"]).query

    from src.guardrails.pii import redact_pii
    query = redact_pii(query)

    print("Validate_reserach_scope starts", flush=True)
    validate_research_scope(query)
    print("validate_reserach_scope ends", flush=True)

    return {"user_query": query}

#synchronous in-memory transformation
def query_analyzer_node(state: QuantPilotState) -> dict:
    """Analyze the user's research query."""

    #research_query = analyze_query(state["user_query"])

    print("analyze_query_with_context starts", flush= True)
    research_query, start, end = analyze_query_with_context(
    query=state["user_query"],
    ticker=state["ticker"],
    default_start=state["start"],
    default_end=state["end"],
    )

    #print(f"\nreaserach_query:-{'-'*70}\n{research_query}", flush=True)

    print("analyze_query_with_context ends", flush= True)


    return {"research_query": research_query, "start": start, "end": end,}

#synchronous in-memory transformation
def research_planner_node(state: QuantPilotState) -> dict:
    """Create a research plan from the analyzed query."""

    '''Below we don't do state.get("research_query", "") because that masks the error if research_query is missing. 
    so we use state.get("research_query") and check for None(raise an error is it is None) 
    to ensure that research_query is present before proceeding to create the research plan.'''
    #research_plan = create_research_plan(state["research_query"])
    research_query = state.get("research_query")

    if research_query is None:
        raise RuntimeError(
            "research_query is missing before research_planner."
        )

    print("create_research_plan strrt", flush=True)
    research_plan = create_research_plan(research_query)
    print("create_research_plan ends", flush=True)

    return {"research_plan": research_plan,}

'''
def research_executor_node(state: QuantPilotState) -> dict:
    """Execute the current research plan."""

    execution_sequence = execute_research_plan(state["research_plan"], state["ticker"], 
    state["start"], state["end"], state.get("financial_metrics"))

    return {
        "research_results": [
            {"step": result}
            for result in execution_sequence
        ],
    }
'''

#asynchornous transformation
async def research_executor_node(state: QuantPilotState,) -> dict:

    ''' Below we don't do state.get("research_plan", "") because that masks the error if research_plan is missing.
    so we use state.get("research_plan") and check for None(raise an error is it is None) to ensure that research_plan 
    is present before proceeding to execute the research plan.'''
    research_plan = state.get("replan_plan") or state.get("research_plan") #earlier research_plan = state.get("research_plan")

    if research_plan is None:
        raise RuntimeError("research_plan is missing before research_executor.")

    print("execute_research_plan starts", flush=True)
    execution_sequence = await execute_research_plan(
        research_plan= research_plan,
        ticker=state["ticker"],
        start=state["start"],
        end=state["end"],
        financial_metrics=state.get("financial_metrics"),
        replan_financial_metrics=state.get("replan_financial_metrics"),
        #added for dynamic finacial list created in replan o/p for incremental tool_cat='financial'
        #for non-financial_anaylysis,
        replan_count= state.get("replan_count", 0),#to tackle augmneteed  extrenal serach(max_results=10)
        existing_results=state.get("research_results"),
    )
    print("execute_research_plan ends", flush=True)

    #diagnosis patch strat-----------------------------------------

    
    existing_results = state.get("research_results", [])

    print(
        "Existing step_ids:",
        [item.get("step_id") for item in existing_results],
    )
    print(
        "New execution step_ids:",
        [item.get("step_id") for item in execution_sequence],
    )
    print(
        "Combined step_ids:",
        [
            item.get("step_id")
            for item in existing_results + execution_sequence
        ],
    )

    #diagnosis patch ends

    return {
        "research_results": (
            state.get("research_results", []) + execution_sequence
        ),
    }

#synchronous in-memory transformation
def evidence_builder_node(state: QuantPilotState) -> dict:
    research_results = state.get("research_results")

    if research_results is None:
        raise ValueError("research_results are required to build evidence.")

    print("build_evidence_ledger starts", flush=True)
    evidence_ledger = build_evidence_ledger(
        research_results,
        previous_evidence=state.get("evidence"),
    )
    print("build_evidence_ledger ends", flush=True)

    return {"evidence": evidence_ledger,}

#synchronous in-memory transformation
def thesis_node(state: QuantPilotState) -> dict:
    evidence = state.get("evidence")

    if evidence is None:
        raise ValueError("evidence is required to generate a thesis.")

    print("generate_thesis starts", flush=True)
    thesis = generate_thesis(
        user_query=state["user_query"],
        evidence=evidence,
    )
    print("generate_thesis ends", flush=True)

    return {"thesis": thesis}

#synchronous in-memory transformation
def devil_advocate_node(state: QuantPilotState) -> dict:
    research_query = state.get("research_query")
    thesis = state.get("thesis")
    evidence = state.get("evidence")

    replan_count= state.get("replan_count", 0)
    replan_financial_metrics=state.get("replan_financial_metrics")


    if evidence is None or thesis is None or research_query is None:
        raise ValueError("All evidence and thesis and research_query are required to generate a critique of thesis")

    print("critique_thesis starts", flush=True)
    critique = critique_thesis(thesis, evidence, research_query, replan_count, replan_financial_metrics)
    print("critique_thesis ends", flush=True)

    return {"critique": critique}

#synchronous in-memory transformation
def evidence_adjudicator_node(state: QuantPilotState) -> dict:
    thesis = state.get("thesis")
    critique = state.get("critique")
    evidence = state.get("evidence")

    #print(f"crtique/DA o/p:{critique}")

    if thesis is None or critique is None or evidence is None:
        raise ValueError(
            "Thesis, critique, and evidence are required for adjudication"
        )

    print("adjudicate_evidence starts", flush=True)
    adjudication = adjudicate_evidence(thesis, critique, evidence,)
    print("adjudicate_evidence ends", flush=True)

    return {"adjudication": adjudication}


def route_after_adjudication(state: QuantPilotState) -> str:
    adjudication = state.get("adjudication")

    #print(f"adjudication_o/p:-{adjudication}")

    if adjudication is None:
        raise ValueError("Adjudication is required for routing")

    if adjudication.decision == "PASS":
        logger.info("Routing: PASS → final_report")
        return "final_report"

    if state.get("replan_count", 0) < MAX_REPLANS:
        logger.info(
            "Routing: FAIL → replan | replan_count=%s/%s",
            state.get("replan_count",0), MAX_REPLANS
        )
        return "replan"

    logger.info("Routing: FAIL → final_report | maximum replans reached")
    return "final_report"

def final_report_node(state: QuantPilotState) -> dict:
    thesis = state.get("thesis")
    evidence = state.get("evidence")
    adjudication = state.get("adjudication")
    research_results = state.get("research_results")

    research_plan=state.get("research_plan")

    user_query=state["user_query"]




    if thesis is None or research_plan is None or adjudication is None or research_results is None:
        raise ValueError(
            "Thesis, reserach_plan, research_results and adjudication are required for final report"
        )

    print("generate_final_report starts", flush=True)
    final_report = generate_final_report(
        thesis = thesis,
        #evidence= evidence,
        adjudication = adjudication,
        research_results = research_results,
        user_query= user_query,
        research_plan= research_plan,

        replan_plan=state.get("replan_plan"),#optional fields
        financial_metrics=state.get("financial_metrics"),#optional fields
        replan_financial_metrics=state.get("replan_financial_metrics"),#optional_fields
    )
    print("generate_final_report ends", flush=True)

    return {"final_report": final_report}

def replan_node(state: QuantPilotState) -> dict:
    adjudication = state.get("adjudication")
    evidence = state.get("evidence")
    research_query = state.get("research_query")

    if adjudication is None or evidence is None or research_query is None:
        raise ValueError(
            "Adjudication and research query are required for re-planning"
        )

    replan_count = state.get("replan_count", 0)

    if state.get("replan_count", 0) >= MAX_REPLANS:
        raise ValueError("Maximum replan attempts exceeded")

    print("replan_research starts", flush=True)
    replan_plan, replan_financial_metrics = replan_research(research_query, evidence,
                                                             adjudication,)
    print("replan_research ends", flush=True)

    #print(f"replan_financial_metrics:-{replan_financial_metrics}")

    return {
        "replan_plan": replan_plan,
        "replan_financial_metrics": replan_financial_metrics,
        "replan_count": replan_count + 1,
    }

def output_guardrail_node(state: QuantPilotState) -> dict:
    report = state.get("final_report")

    if report is None:
        raise ValueError("Final report is required for output validation.")

    print("validate_final_report starts", flush=True)
    final_report = validate_final_report(report)
    print("validate_final_report ends", flush=True)

    return {"final_report": final_report}


def build_quantpilot_graph(checkpointer=None):#earlier no ckpt argument
    """Build the initial QuantPilot LangGraph workflow."""

    graph = StateGraph(QuantPilotState)

    graph.add_node("input_guardrails", _logged_node("input_guardrails", input_guardrails_node) )
    graph.add_node("query_analyzer", _logged_node("query_analyzer", query_analyzer_node) )
    graph.add_node("research_planner", _logged_node("research_planner", research_planner_node) )
    graph.add_node("research_executor", _logged_node("research_executor", research_executor_node) )
    graph.add_node("evidence_builder", _logged_node("evidence_builder", evidence_builder_node) )
    graph.add_node("thesis", _logged_node("thesis", thesis_node) )
    graph.add_node("devil_advocate", _logged_node("devil_advocate", devil_advocate_node) )
    graph.add_node("evidence_adjudicator", _logged_node("evidence_adjudicator", evidence_adjudicator_node) )
    graph.add_node("final_report", _logged_node("final_report", final_report_node) )
    graph.add_node("replan", _logged_node("replan", replan_node) )
    graph.add_node("output_guardrail", _logged_node("output_guardrail", output_guardrail_node) )

    
    graph.add_edge(START, "input_guardrails")
    graph.add_edge("input_guardrails", "query_analyzer")
    graph.add_edge("query_analyzer", "research_planner")
    graph.add_edge("research_planner", "research_executor")
    graph.add_edge("research_executor", "evidence_builder")
    graph.add_edge("evidence_builder", "thesis")
    graph.add_edge("thesis", "devil_advocate")
    graph.add_edge("devil_advocate", "evidence_adjudicator")

    graph.add_conditional_edges(
        "evidence_adjudicator",
        route_after_adjudication,
        {
            "final_report": "final_report",
            "replan": "replan",
        },
    )

    graph.add_edge("replan", "research_executor")
    graph.add_edge("final_report", "output_guardrail")
    graph.add_edge("output_guardrail", END)
    

    return graph.compile(checkpointer=checkpointer)#earlier no ckpt argument

@asynccontextmanager
async def compiled_quantpilot_graph():
    async with AsyncSqliteSaver.from_conn_string(
        "data/quantpilot_checkpoints.sqlite3"
    ) as checkpointer:
        
        yield build_quantpilot_graph(checkpointer)