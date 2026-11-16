from datetime import date
import asyncio

from src.graph.workflow import build_quantpilot_graph, compiled_quantpilot_graph
from src.graph.state import QuantPilotState

from langchain_core.runnables import RunnableConfig

initial_state=QuantPilotState({
    #"user_query": "Analyze Apple's historical volatility.",#case-B(a); without input fin_metruc:- caseB(b)
    #"user_query":"Analyze apple's valuation & historical volatility.",#case 1(with metrics)
    #"user_query": "Analyze apple's valuation and fiftyDayAverage.",
    #"user_query": "Compare Apple's valuation, and market trend.",#w/o input fin_metrics;case(C)
    "user_query": "Compare Apple's returns and valuation, beta and market trend.",# this 
    #query will qulaify #for fina;_node in 2nd re-planne run (because of task-wise 
    # incremental tool exceution in 2nd run(we cahnged the coomon tool union set to task-
    # specific tool exceution adjudicator check).
    #also this query shall yeid 3 task_types:-'compare','financial'(valuation)&
    # qualification_analysis'
    "ticker": "AAPL",
    "start": date(2025, 1, 9),
    "end": date(2025, 1, 16),
    "financial_metrics": ["trailingPE", "marketCap",],
})

def output_print(result):
    for key in result.keys():
        print(f"{key}:-{result.get(key)}")
        print("-"*70)
    
    #print(f"research_results:-{result['research_results']}")

    final_report = result.get('final_report')
    #print(f"final_report:-{final_report}")

    if(final_report):
        for key, value in final_report.model_dump().items():
        #model_dump needed with pydatic model object(final_report)
            if(key=='normalized_results'):
                print(f"{key}:-")
                [print (f"{elm}\n{'~'*50}") for elm in value]
            else:
                print(f"{key}:-{value}\n{'-'*80}")

#----------------noraml graph initialization &run------
'''
async def main():# ear;ier non-async main() function used.

    
    graph = build_quantpilot_graph()
    result = await graph.ainvoke(initial_state)
'''
#-------------------------------------------------------

#------------LangGraph workflow checkpointing----graph initilazation& run---


async def main():
    #sets config as of RunnableConfig type to avert RunnableConfig-->dict[str, dict[str]] mismatch error
    config: RunnableConfig={"configurable": {"thread_id": "quantpilot-run-4task_tpes_001"} }

    
    ##checkpoint persistance verification logic
    # Run the workflow and verify its final checkpoint.
    async with compiled_quantpilot_graph() as graph:

        print("Starting QuantPilot graph...", flush=True)
        
        for node in graph.get_graph().nodes:
            print(node, flush=True)

        result = await graph.ainvoke(initial_state, config=config,)
        print("Graph completed.", flush=True)

        output_print(result)

        snapshot = await graph.aget_state(config)

        print(
            "Final report checkpointed:",
            snapshot.values.get("final_report") is not None,
        )
        print(
            "Replan count:",
            snapshot.values.get("replan_count"),
        )

    # Close and reopen the checkpointer, then verify persistence.
    async with compiled_quantpilot_graph() as graph:
        snapshot = await graph.aget_state(config)

        print(
            "Final report persisted after reopen:",
            snapshot.values.get("final_report") is not None,
        )


#------------LangGraph workflow checkpointing----end-----------------------------    

if __name__ == "__main__":
    #main()
    asyncio.run(main())

