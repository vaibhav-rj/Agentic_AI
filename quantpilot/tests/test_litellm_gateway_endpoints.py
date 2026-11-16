import pytest

from src.llm import litellm_gateway as gateway
from src.llm.config import HostedModelConfig, REASONING

'''
@pytest.mark.parametrize(
    "api_base",
    [
        "https://api.cloudflare.com/client/v4/accounts/test/ai/v1",
        "https://ai-gateway.kilo.ai/api/v1",
        None,
    ],
)
def test_build_model_list_api_base(monkeypatch, api_base):
    config = HostedModelConfig(
        model_id="test-model",
        provider="test",
        litellm_model="openai/test-model",
        max_new_tokens=256,
        capabilities=REASONING,
        priority=1,
        api_key_env="TEST_API_KEY",
        api_base=api_base,
    )

    monkeypatch.setenv("TEST_API_KEY", "test-key")
    monkeypatch.setattr(
        gateway, "MODEL_CANDIDATES", {"reasoning": (config,)}
    )

    deployments, candidates = gateway._build_model_list("reasoning")

    params = deployments[0]["litellm_params"]

    assert params["model"] == "openai/test-model"
    assert params["api_key"] == "test-key"
    assert params["order"] == 1
    assert params.get("api_base") == api_base
    assert candidates == [config,]
'''


@pytest.mark.parametrize(
    "provider,expected_base",
    [
        (
            "cloudflare",
            "https://api.cloudflare.com/client/v4/accounts/test-account/ai/v1",
        ),
        (
            "kilocode",
            "https://ai-gateway.kilo.ai/api/v1",
        ),
        ("groq", None),
        ("nvidia", None),
        ("gemini", None),
    ],
)
def test_provider_endpoint_resolution(
    monkeypatch, provider, expected_base
):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")

    config = HostedModelConfig(
        model_id="test-model",
        provider=provider,
        litellm_model="openai/test-model",
        max_new_tokens=256,
        capabilities=REASONING,
        priority=1,
        api_key_env="TEST_API_KEY",
    )

    monkeypatch.setenv("TEST_API_KEY", "test-key")
    monkeypatch.setattr(
        gateway, "MODEL_CANDIDATES", {"reasoning": (config,)}
    )

    deployments, candidates = gateway._build_model_list("reasoning")

    params = deployments[0]["litellm_params"]

    assert params["api_key"] == "test-key"
    assert params["order"] == 1
    assert params.get("api_base") == expected_base
    assert candidates == [config]


def test_cloudflare_missing_account_id(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)

    config = HostedModelConfig(
        model_id="test-model",
        provider="cloudflare",
        litellm_model="openai/test-model",
        max_new_tokens=256,
        capabilities=REASONING,
        priority=1,
        api_key_env="TEST_API_KEY",
    )

    monkeypatch.setenv("TEST_API_KEY", "test-key")
    monkeypatch.setattr(
        gateway, "MODEL_CANDIDATES", {"reasoning": (config,)}
    )

    deployments, _ = gateway._build_model_list("reasoning")

    assert "api_base" not in deployments[0]["litellm_params"]