from unittest.mock import patch

from src.llm.litellm_gateway import get_litellm_model


@patch("src.llm.litellm_gateway.ChatLiteLLMRouter", create=True)
@patch("litellm.router.Router")
@patch("src.llm.litellm_gateway._build_model_list")
def test_router_configuration(mock_build, mock_router, mock_adapter):

    deployment = {
        "model_name": "quantpilot-reasoning",
        "litellm_params": {
            "model": "groq/test-model",
            "order": 1,
            "temperature": 0.1,
            "max_tokens": 512,
        },
        "model_info": {"id": "reasoning-1-0"},
    }

    candidate = type("Candidate", (), {
        "provider": "groq",
        "model_id": "test-model",
        "priority": 1,
        "temperature": 0.1,
        "max_new_tokens": 512,
    })()

    mock_build.return_value = ([deployment], [candidate])

    mock_router.return_value.model_list = [deployment]
    mock_adapter.return_value = object()

    get_litellm_model.cache_clear()

    try:
        get_litellm_model("reasoning")
        kwargs = mock_router.call_args.kwargs

        assert kwargs["routing_strategy"] == "simple-shuffle"
        assert kwargs["enable_weighted_failover"] is False
        assert kwargs["num_retries"] == 3
        assert kwargs["cooldown_time"] == 5
        assert kwargs["cache_responses"] is True

    finally:
        get_litellm_model.cache_clear()