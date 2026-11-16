from datetime import date

from src.schemas.research import ResearchPlan

'''
from src.tools.financials import get_financial_metrics
from src.tools.market import get_historical_prices
from src.tools.quant import (
    calculate_max_drawdown,
    calculate_return_series,
    calculate_total_return,
    calculate_volatility,
)
'''
from langchain_core.messages import SystemMessage, HumanMessage
from src.mcp.client import call_server

import json
from src.llm import invoke_with_fallback

import logging
logger = logging.getLogger(__name__)

#for stripping transient fields
def strip_fn(existing_data: dict) -> dict:
    return {
        key: value
        for key, value in existing_data.items()
        if key not in {"step_id", "task_type", "tool_category"}
    }

#reserach_query tavily sercah results enchnacement
def enhance_research_result(result: dict, max_chars: int = 4000) -> dict:
    sources = result.get("sources", [])
    if not sources:
        return result

    source_text = json.dumps(
        [
            {
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "content": s.get("content", ""),
            }
            for s in sources
        ],
        ensure_ascii=False,
    )

    messages = [
        SystemMessage(content=rf"""
    Synthesize the following Tavily research sources into a clear,
    concise financial-research summary of at most {max_chars} characters.

    Preserve material facts, figures, dates, caveats and disagreements.
    Distinguish source publication dates and historical coverage from
    the requested market-analysis period. Do not imply temporal alignment
    unless supported by the sources; acknowledge uncertainty when dates
    or coverage cannot be established.

    Do not invent information. Attribute claims using source titles/URLs.
    Remove duplication without implying unsupported certainty. 
    """),
        HumanMessage(content=f"""
    Sources:
    {source_text}
    """)
    ]

    try:
        response = invoke_with_fallback("reasoning", messages)
        logger.info("External research synthesized summary completed")

        summary = getattr(response, "content", response)

        if not isinstance(summary, str) or not summary.strip():
            return result

        return {**result, "synthesized_summary": summary.strip()[:max_chars]}

    except Exception:
        logger.warning("External research synthesized summary failed, although tavily source.content remians")
        return result
    
async def execute_research_plan(
    research_plan: ResearchPlan,
    ticker: str,
    start: date,
    end: date,
    financial_metrics: list[str] | None = None,
    replan_financial_metrics: list[str] | None = None,#dynamically added(not in input for task ! finacial_analysis)
    replan_count: int=0,
    existing_results: list[dict] | None = None,
) -> list[dict]:


    """Execute only research work not already available."""

    results: list[dict] = []
    computed_results: dict[str, dict] = {}# new addition(after task_type in steps included)

    existing_results = existing_results or []

    market_data = next(
        (
            result["result"]
            for result in existing_results
            if result["tool_category"] == "market"
        ),
        None,
    )

    existing_market = next(
        (
            strip_fn(result)
            for result in existing_results
            if result["tool_category"] == "market"
        ),
        None,
    )


    existing_financial = next(
        (
            strip_fn(result)
            for result in existing_results
            if result["tool_category"] == "financial"
        ),
        None,
    )

    existing_research = next(
        (
            strip_fn(result)
            for result in existing_results
            if result["tool_category"] == "research"
        ),
        None,
    )

    existing_quantitative = next(
        (
            strip_fn(result)
            for result in existing_results
            if result["tool_category"] == "quantitative"
        ),
        None,
    )

    #print(f"existing_financial:-{existing_financial}")
    #print(f"financial_metrics:-{financial_metrics}")
    #print(f"replan_financial_metrics:-{replan_financial_metrics}")
    #print('*'*70)

    for step in research_plan.steps:

        logger.info("Executing research step | step_id=%s | task=%s | tool=%s", step.step_id, step.task_type, step.tool_category)

        tool_category = step.tool_category

        #checking if tool_o/p of this run already in computed_results and reusing it
        if tool_category in computed_results:

            results.append({
                "step_id": step.step_id,
                "task_type": step.task_type,
                "tool_category": tool_category,
                **computed_results[tool_category],
            })
            continue

        
        if tool_category == "market":

            #reusing exusting data
            if existing_market is not None:
                computed_results[tool_category] = existing_market#store exiting data in computed results

                results.append({
                    "step_id": step.step_id,
                    "task_type": step.task_type,
                    "tool_category": tool_category,
                    **existing_market,
                })

                continue
            
            #fresh tool run
            market_data = await call_server(
                "src.mcp.market_server",
                "historical_prices",
                {
                    "ticker": ticker,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
            )

            '''
            results.append({
                "step_id": step.step_id,
                "tool_category": "market",
                "tool": "historical_prices",
                "result": market_data,
            })
            '''
            #result_update in computed_results
            computed_results[tool_category] = {
                "tool": "historical_prices",
                "result": market_data,
            }

            results.append({
                "step_id": step.step_id,
                "task_type": step.task_type,
                "tool_category": tool_category,
                **computed_results[tool_category],
            })
            

        elif tool_category == "financial":
            '''#earlier case when dynamic financial metric not in picture
            if not financial_metrics:
                raise ValueError(
                    "financial_metrics are required for financial research."
                )
            '''
            #new case:-when dynamic finnacial metroc generated for incremntal replanned run of
            #task_types(presently finacial/quantitaive/market_analysis)

            #could also reuse old metrics as requeset metrics in case of nil replan/dynamic  fin metriocs
            #-->therby use tool_cat='financial' calculation/calc reuse from plan run for 
            # incrememtal runs of other task_types (qunatittiave/market)analysis)
            requested_metrics = (
                replan_financial_metrics
                if replan_financial_metrics#(to negate both [] and None together), earlier only restructed to None
                else financial_metrics
            )

            #print(f"requested_metrocs:-{requested_metrics}\n{'`'*90}")

            #handle corner cases where no input financial metrics, and dynamic financial metrics are 
            # also none, so to void workflow breakdwon from necxt exception error at same indent
            #Exception:- Financial_analysis must have initial written financial_metric, else error thrown
            #@ line 194
            if not requested_metrics:
                if not step.required:
                    results.append({
                        "step_id": step.step_id,
                        "task_type": step.task_type,
                        "tool_category": tool_category,
                        "tool": "financial_metrics",
                        "result": None,
                        #"skipped": True,#skipped:-True(means no tool ops)
                    })
                    continue

                raise ValueError(#if no initail finacial_metrics and plan run has task_type="financial_analysis"
                    "Financial metrics are required for financial research."
                )
            
            if not requested_metrics:
                raise ValueError(
                    "Financial metrics are required for financial research."
                )

            #dynamic replan_finacila_metrics as well as origonal explicit input finacial_metrics 
            # handling complete

            existing_metrics = [metric["name"] for metric in (existing_financial or {}).get
                                ("result", {}).get("metrics", [])]

            #print(f"existing_metrics:-{existing_metrics}")

            missing_metrics = [
                metric
                for metric in requested_metrics #finacial_metrics-->requested_metrics
                if metric not in existing_metrics
            ]

            #print(f"missing_metrics:-{missing_metrics}")

            #reusing existing data. these would handle cases, when finacial tool_cat run in plan ietration,
            #but the dyanmic financial metriv=cs are nil for incremental finacial tool_cat run
            if not missing_metrics and existing_financial is not None:

                computed_results[tool_category] = existing_financial#store exiting data in computed results
            
                results.append({
                    "step_id": step.step_id,
                    "task_type": step.task_type,
                    "tool_category": tool_category,
                    **existing_financial,
                })
                continue

            #fresh tool run(shall also run in cazsez expicit financial metrics in 
            # input but not utilized in 1st plan run as no finacial_analysis task--->but usable 
            # in increnmetal finace tool_cat run for other task_types:- qualitative/market_nanalyis)

            financial_data = await call_server(
                "src.mcp.financial_server",
                "financial_metrics",
                {
                    "ticker": ticker,
                    "metrics": missing_metrics,
                },
            )

            '''
            results.append({
                "step_id": step.step_id,
                "tool_category": "financial",
                "tool": "financial_metrics",
                "result": financial_data,
            })
            '''
            #print(f"financial_data:-{financial_data}")

            #mixing the incomplete existing + new metrics before update to compute _result and 
            #appendage
            previous_metrics_list = [metric for metric in (existing_financial or {}).get
                                ("result", {}).get("metrics", [])]
            new_metrics_list = [metric for metric in financial_data.get("metrics", [])]

            merged_metrics_list = previous_metrics_list + new_metrics_list

            merged_data ={
                "ticker": ticker,
                "metrics": merged_metrics_list
            }

            #result_update in computed_results
            computed_results[tool_category] = {
                "tool": "financial_metrics",
                "result": merged_data,
            }

            results.append({
                "step_id": step.step_id,
                "task_type": step.task_type,
                "tool_category": tool_category,
                **computed_results[tool_category],
            })

        elif tool_category == "quantitative":
            if market_data is None:
                raise RuntimeError(
                    "Quantitative analysis requires market data first."
                )

            existing_tools = set(
                (existing_quantitative or {}).get("tools", [])
            )

            total_return = None
            return_data = None
            volatility = None
            max_drawdown = None

            if "total_return" not in existing_tools:

                #fresh run
                total_return = await call_server(
                    "src.mcp.quant_server",
                    "total_return",
                    {"prices": market_data},
                )

            if "return_series" not in existing_tools:

                #fresh run
                return_data = await call_server(
                    "src.mcp.quant_server",
                    "return_series",
                    {"prices": market_data},
                )
            else:
                return_data = (existing_quantitative or {}).get(
                    "result", {}
                ).get("return_series")

            if (
                "volatility" not in existing_tools
                and return_data is not None
            ):
                #fresh run
                volatility = await call_server(
                    "src.mcp.quant_server",
                    "volatility",
                    {"returns": return_data},
                )

            if "max_drawdown" not in existing_tools:

                #fresh run
                max_drawdown = await call_server(
                    "src.mcp.quant_server",
                    "max_drawdown",
                    {"prices": market_data},
                )
            #reusing exusting data
            if(total_return==None and volatility ==None
               and max_drawdown ==None and existing_quantitative is not None):

                computed_results[tool_category] = existing_quantitative#store exiting data in computed results
                
                results.append({
                    "step_id": step.step_id,
                    "task_type": step.task_type,
                    "tool_category": tool_category,
                    **existing_quantitative,
                })
                continue

            new_quantitative = {}

            if total_return is not None:
                new_quantitative["total_return"] = total_return

            if return_data is not None and "return_series" not in existing_tools:
                new_quantitative["return_series"] = return_data

            if volatility is not None:
                new_quantitative["volatility"] = volatility

            if max_drawdown is not None:
                new_quantitative["max_drawdown"] = max_drawdown

            if new_quantitative:
                '''
                results.append({
                    "step_id": step.step_id,
                    "tool_category": "quantitative",
                    "tools": list(new_quantitative.keys()),
                    "result": new_quantitative,
                })
                '''
                #result_update in computed_results(along with append)

                #very critical(merges the results of existing-when boroken+ new when icompltete)
                combined_quantitative = {
                    **(existing_quantitative or {}).get("result", {}),
                    **new_quantitative,
                }

                #combibed storage
                computed_results[tool_category] = {
                    "tools": list(combined_quantitative.keys()),
                    "result": combined_quantitative,
                }

                #combined complete appendage
                results.append({
                    "step_id": step.step_id,
                    "task_type": step.task_type,
                    "tool_category": tool_category,
                    **computed_results[tool_category],
                })
            

        elif tool_category == "research":
            
            #reusing exusting data
            '''
            if existing_research is not None:
                computed_results[tool_category] = existing_research#store exiting data in computed results

                results.append({
                    "step_id": step.step_id,
                    "task_type": step.task_type,
                    "tool_category": tool_category,
                    **existing_research,
                })

                continue
            '''

            research_input = (" ".join(research_plan.research_questions).strip() or research_plan.query)

            original_input = research_plan.query
        
            #fresh run
            research_data = await call_server(
                "src.mcp.research_server",
                "research_query",
                {"research_query": research_input, "original_query": original_input, "max_results":5} 
                if (replan_count==1) else {"research_query": research_input, "max_results": 5},
                #erlier:- reserach_query.query
            )

            research_enhanced =enhance_research_result(research_data)

            '''
            results.append({
                "step_id": step.step_id,
                "tool_category": "research",
                "tool": "research_query",
                "result": research_data,
            })
            '''
            #result_update in computed_results
            computed_results[tool_category] = {
                "tool": "research_query",
                "result": research_enhanced,
            }

            results.append({
                "step_id": step.step_id,
                "task_type": step.task_type,
                "tool_category": tool_category,
                **computed_results[tool_category],
            })

        else:
            raise ValueError(
                f"Unsupported tool category: {step.tool_category}"
            )

    logger.info("Research execution completed | results=%d", len(results))
    return results
