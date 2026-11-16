
import asyncio
import json
import logging

from datetime import date, datetime
from enum import Enum
from pathlib import Path

from langchain_core.runnables import RunnableConfig

from src.graph.workflow import compiled_quantpilot_graph
from src.graph.state import QuantPilotState


# ---------------- Sample input ----------------

# QP19 — Business identifier redaction
initial_state = QuantPilotState({
    "user_query": "Hi",
    "ticker": "AAPL",
    "start": date(2025, 1, 1),
    "end": date(2025, 4, 1),
    "financial_metrics": ["trailingPE", "marketCap"],
},)


# ---------------- Serialization ----------------

def json_default(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value

    raise TypeError(
        f"Object of type {type(value).__name__} is not JSON serializable"
    )


def save_state(state, filepath):
    with filepath.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=4, default=json_default)


# ---------------- Evaluation run ----------------

async def main():

    # Unique directory for every sample run
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_dir = Path("QuantPilot_Samples") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Root handler receives propagated module logs
    logging.basicConfig(
        filename=run_dir / "quantpilot.log",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )

    logger = logging.getLogger(__name__)

    # Unique checkpoint thread for this run
    config: RunnableConfig = {
        "configurable": {"thread_id": f"quantpilot-{run_id}"}
    }

    # Save input before execution
    save_state(initial_state, run_dir / "initial_state.json")

    async with compiled_quantpilot_graph() as graph:

        result = await graph.ainvoke(initial_state, config=config)

        # Save final workflow state
        save_state(result, run_dir / "final_state.json")

        # Verify final checkpoint
        snapshot = await graph.aget_state(config)

        logger.info(
            "Checkpoint verification | final_report=%s | replan_count=%s",
            snapshot.values.get("final_report") is not None,
            snapshot.values.get("replan_count"),
        )

        print(
            "Workflow completed | Final report checkpointed:",
            snapshot.values.get("final_report") is not None,
        )

    # Reopen graph and verify checkpoint persistence
    async with compiled_quantpilot_graph() as graph:

        snapshot = await graph.aget_state(config)

        print(
            "Checkpoint persisted after reopen:",
            snapshot.values.get("final_report") is not None,
        )


if __name__ == "__main__":
    asyncio.run(main())
