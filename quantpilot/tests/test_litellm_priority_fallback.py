import pytest
from unittest.mock import patch

from litellm.router import Router


@pytest.mark.asyncio
async def test_vertical_priority_fallback():

    model_list = [
        {
            "model_name": "quantpilot-test",
            "litellm_params": {
                "model": "openai/tier1-a",
                "api_key": "test",
                "order": 1,
            },
            "model_info": {"id": "tier1-a"},
        },
        {
            "model_name": "quantpilot-test",
            "litellm_params": {
                "model": "openai/tier1-b",
                "api_key": "test",
                "order": 1,
            },
            "model_info": {"id": "tier1-b"},
        },
        {
            "model_name": "quantpilot-test",
            "litellm_params": {
                "model": "openai/tier2-a",
                "api_key": "test",
                "order": 2,
            },
            "model_info": {"id": "tier2-a"},
        },
        {
            "model_name": "quantpilot-test",
            "litellm_params": {
                "model": "openai/tier2-b",
                "api_key": "test",
                "order": 2,
            },
            "model_info": {"id": "tier2-b"},
        },
    ]

    router = Router(
        model_list=model_list,
        routing_strategy="simple-shuffle",
        enable_weighted_failover=False,
        num_retries=0,
        cooldown_time=5,
    )

    attempted = []

    def fake_completion(*args, **kwargs):
        model = kwargs.get("model")
        attempted.append(model)

        # Fail priority 1; allow priority 2.
        if model in {"openai/tier1-a", "openai/tier1-b"}:
            raise Exception("Simulated provider failure")

        return {
            "id": "test-response",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "fallback-success",
                },
                "finish_reason": "stop",
            }],
            "created": 0,
            "model": model,
            "object": "chat.completion",
        }

    with patch("litellm.main.completion", side_effect=fake_completion):
        response = await router.acompletion(
            model="quantpilot-test",
            messages=[{"role": "user", "content": "test"}],
        )

    #assert response.choices[0].message.content == "fallback-success"
    assert response["choices"][0]["message"]["content"] == "fallback-success"
    assert attempted, "No deployment was attempted"

    # Initial selection must be from priority 1.
    assert attempted[0] in {
        "openai/tier1-a",
        "openai/tier1-b",
    }

    # Successful fallback must be from priority 2.
    assert attempted[-1] in {
        "openai/tier2-a",
        "openai/tier2-b",
    }

    print(f"\nAttempted deployments:{attempted}")
    print(f"Unique deployments:{set(attempted)}")
    # No repeated horizontal retry of the same deployment.
    assert len(attempted) == len(set(attempted))