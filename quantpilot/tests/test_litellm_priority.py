import inspect
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from litellm.router import Router

from src.llm.config import LITELLM_MODEL_GROUPS
from src.llm.litellm_gateway import _build_model_list


load_dotenv()


@pytest.mark.parametrize("role", ["reasoning", "judge", "guardrail"])
@pytest.mark.asyncio
async def test_priority_fallback_1_to_2_to_3(role):
    # Use the actual configured deployments and priorities.
    deployments, _ = _build_model_list(role)
    priorities = sorted({
        deployment["litellm_params"]["order"]
        for deployment in deployments
    })

    assert priorities[:3] == [1, 2, 3], (
        f"{role}: expected priorities 1, 2 and 3; found {priorities}"
    )

    router = Router(
        model_list=deployments,
        routing_strategy="simple-shuffle",
        cache_responses=False,
    )

    attempted_priorities = []

    # Simulate priority 2 failing and priority 3 succeeding.
    async def fake_run_async_fallback(*args, **kwargs):
        fallback_entries = kwargs["fallback_model_group"]

        for entry in fallback_entries:
            priority = entry["_target_order"]
            attempted_priorities.append(priority)

            if priority == 2:
                continue  # Simulated provider failure

            if priority == 3:
                return {"simulated_success_priority": 3}

        raise AssertionError("Priority 3 was not reached")

    router_module = inspect.getmodule(Router)

    with patch.object(
        router_module,
        "run_async_fallback",
        new=fake_run_async_fallback,
    ):
        result = await router.async_function_with_fallbacks_common_utils(
            e=RuntimeError("Simulated priority-1 failure"),
            disable_fallbacks=False,
            fallbacks=None,
            context_window_fallbacks=None,
            content_policy_fallbacks=None,
            model_group=LITELLM_MODEL_GROUPS[role],
            args=(),
            kwargs={
                "model": LITELLM_MODEL_GROUPS[role],
                "_target_order": 1,
            },
        )

    assert attempted_priorities == [2, 3]
    assert result == {"simulated_success_priority": 3}

#Same-priority load balancing
def test_same_priority_deployments_are_balanced():
    import random

    model_name = "test-reasoning"

    model_list = [
        {
            "model_name": model_name,
            "litellm_params": {
                "model": "openai/test-model-a",
                "api_key": "test-key",
                "order": 1,
            },
        },
        {
            "model_name": model_name,
            "litellm_params": {
                "model": "openai/test-model-b",
                "api_key": "test-key",
                "order": 1,
            },
        },
    ]

    router = Router(
        model_list=model_list,
        routing_strategy="simple-shuffle",
        cache_responses=False,
    )

    random_state = random.getstate()
    try:
        random.seed(42)

        selected = {
            router.get_available_deployment(model=model_name)
            ["litellm_params"]["model"]
            for _ in range(30)
        }
    finally:
        random.setstate(random_state)

    assert selected == {
        "openai/test-model-a",
        "openai/test-model-b",
    }


#Fallback tiers are exhausted in ascending order
@pytest.mark.parametrize("role", ["reasoning", "judge", "guardrail"])
@pytest.mark.asyncio
async def test_fallback_tiers_are_attempted_in_order(role):
    deployments, _ = _build_model_list(role)

    priorities = sorted({
        d["litellm_params"]["order"]
        for d in deployments
    })

    router = Router(
        model_list=deployments,
        routing_strategy="simple-shuffle",
        cache_responses=False,
    )

    attempted = []

    async def fake_run_async_fallback(*args, **kwargs):
        entries = kwargs["fallback_model_group"]
        attempted.extend(
            entry["_target_order"] for entry in entries
        )
        return {"simulated_success": True}

    router_module = inspect.getmodule(Router)

    with patch.object(
        router_module,
        "run_async_fallback",
        new=fake_run_async_fallback,
    ):
        await router.async_function_with_fallbacks_common_utils(
            e=RuntimeError("Simulated failure"),
            disable_fallbacks=False,
            fallbacks=None,
            context_window_fallbacks=None,
            content_policy_fallbacks=None,
            model_group=LITELLM_MODEL_GROUPS[role],
            args=(),
            kwargs={
                "model": LITELLM_MODEL_GROUPS[role],
                "_target_order": priorities[0],
            },
        )

    assert attempted == priorities[1:]

#Never skip the next available priority
@pytest.mark.parametrize("role", ["reasoning", "judge", "guardrail"])
@pytest.mark.asyncio
async def test_fallback_starts_with_next_available_priority(role):
    deployments, _ = _build_model_list(role)

    priorities = sorted({
        d["litellm_params"]["order"]
        for d in deployments
    })

    router = Router(
        model_list=deployments,
        routing_strategy="simple-shuffle",
        cache_responses=False,
    )

    attempted = []

    async def fake_run_async_fallback(*args, **kwargs):
        entry = kwargs["fallback_model_group"][0]
        attempted.append(entry["_target_order"])
        return {"success_priority": entry["_target_order"]}

    router_module = inspect.getmodule(Router)

    with patch.object(
        router_module,
        "run_async_fallback",
        new=fake_run_async_fallback,
    ):
        result = await router.async_function_with_fallbacks_common_utils(
            e=RuntimeError("Simulated failure"),
            disable_fallbacks=False,
            fallbacks=None,
            context_window_fallbacks=None,
            content_policy_fallbacks=None,
            model_group=LITELLM_MODEL_GROUPS[role],
            args=(),
            kwargs={
                "model": LITELLM_MODEL_GROUPS[role],
                "_target_order": priorities[0],
            },
        )

    assert attempted == [priorities[1]]
    assert result == {"success_priority": priorities[1]}


