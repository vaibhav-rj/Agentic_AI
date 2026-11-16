from dataclasses import dataclass
from typing import Literal
import os

CLOUDFLARE_API_BASE = (
    "https://api.cloudflare.com/client/v4/accounts/"
    "{account_id}/ai/v1"
)

KILO_API_BASE = "https://ai-gateway.kilo.ai/api/v1"


def resolve_api_base(provider: str) -> str | None:
    if provider == "cloudflare":
        account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        return (
            CLOUDFLARE_API_BASE.format(account_id=account_id)
            if account_id else None
        )

    if provider == "kilocode":
        return KILO_API_BASE

    return None


ModelRole = Literal["reasoning", "judge", "guardrail"]


# ------------------------------------------------------------------
# Capabilities
# ------------------------------------------------------------------

TEXT = frozenset({"text_generation"})
REASONING = TEXT | {"reasoning"}
EVALUATION = TEXT | {"evaluation"}
GUARDRAIL = TEXT | {"instruction_following", "structured_output"}


# ------------------------------------------------------------------
# Hosted model configuration
# ------------------------------------------------------------------

@dataclass(frozen=True)
class HostedModelConfig:
    model_id: str
    provider: str
    litellm_model: str
    max_new_tokens: int
    temperature: float = 0.0
    capabilities: frozenset[str] = TEXT
    priority: int = 100
    api_key_env: str = ""
    enabled: bool = True
    api_base: str | None = None


# Retain the existing import name.
ModelConfig = HostedModelConfig


# ------------------------------------------------------------------
# Hosted model candidates
#
# Original 12 candidates are retained unchanged.
# New candidates are appended after the original four per role.
# Lower priority number = earlier fallback tier.
# ------------------------------------------------------------------

MODEL_CANDIDATES: dict[ModelRole, tuple[HostedModelConfig, ...]] = {

    "reasoning": (
        # Original primary-provider candidates — unchanged
        HostedModelConfig(
            model_id="qwen/qwen3.8-27b",
            provider="groq",
            litellm_model="groq/qwen/qwen3.8-27b",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=1,
            api_key_env="GROQ_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="nvidia/nemotron-3-ultra-550b-a55b",
            provider="nvidia",
            litellm_model="nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=2,
            api_key_env="NVIDIA_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="openai/gpt-oss-120b",
            provider="groq",
            litellm_model="groq/openai/gpt-oss-120b",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=3,
            api_key_env="GROQ_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="gemini-3.5-flash-lite",
            provider="google_genai",
            litellm_model="gemini/gemini-3.5-flash-lite",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=4,
            api_key_env="GOOGLE_API_KEY",
            temperature=0.1,
        ),

        # Cloudflare — Priority 1: strongest reasoning-oriented candidates
        HostedModelConfig(
            model_id="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            provider="cloudflare",
            litellm_model="openai/@cf/meta/llama-3.3-70b-instruct-fp8-fast",#@cf/qwen/qwq-32b
            max_new_tokens=512,
            capabilities=REASONING,
            priority=1,
            api_key_env="CLOUDFLARE_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
            provider="cloudflare",
            litellm_model="openai/@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=1,
            api_key_env="CLOUDFLARE_API_KEY",
            temperature=0.1,
        ),

        # Cloudflare — Priority 2
        HostedModelConfig(
            model_id="@cf/qwen/qwen3-30b-a3b-fp8",
            provider="cloudflare",
            litellm_model="openai/@cf/qwen/qwen3-30b-a3b-fp8",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=2,
            api_key_env="CLOUDFLARE_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="@cf/zai-org/glm-4.7-flash",
            provider="cloudflare",
            litellm_model="openai/@cf/zai-org/glm-4.7-flash",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=2,
            api_key_env="CLOUDFLARE_API_KEY",
            temperature=0.1,
        ),

        # Cloudflare / Kilo — Priority 3
        HostedModelConfig(
            model_id="@cf/nvidia/nemotron-3-120b-a12b",
            provider="cloudflare",
            litellm_model="openai/@cf/nvidia/nemotron-3-120b-a12b",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=3,
            api_key_env="CLOUDFLARE_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="nvidia/nemotron-3.5-lightning:free",
            provider="kilocode",
            litellm_model="openai/nvidia/nemotron-3.5-lightning:free",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=3,
            api_key_env="KILOCODE_API_KEY",
            temperature=0.1,
        ),
        HostedModelConfig(
            model_id="@cf/qwen/qwq-32b",
            provider="cloudflare",
            litellm_model="openai/@cf/qwen/qwq-32b",
            max_new_tokens=512,
            capabilities=REASONING,
            priority=4,
            api_key_env="CLOUDFLARE_API_KEY",
            temperature=0.1,
        ),
    ),

    "judge": (
        # Original primary-provider candidates — unchanged
        HostedModelConfig(
            model_id="qwen/qwen3.8-27b",
            provider="groq",
            litellm_model="groq/qwen/qwen3.8-27b",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=1,
            api_key_env="GROQ_API_KEY",
        ),
        HostedModelConfig(
            model_id="openai/gpt-oss-120b",
            provider="groq",
            litellm_model="groq/openai/gpt-oss-120b",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=2,
            api_key_env="GROQ_API_KEY",
        ),
        HostedModelConfig(
            model_id="nvidia/nemotron-3-ultra-550b-a55b",
            provider="nvidia",
            litellm_model="nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=3,
            api_key_env="NVIDIA_API_KEY",
        ),
        HostedModelConfig(
            model_id="gemini-3.5-flash-lite",
            provider="google_genai",
            litellm_model="gemini/gemini-3.5-flash-lite",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=4,
            api_key_env="GOOGLE_API_KEY",
        ),

        # Cloudflare — Priority 1
        HostedModelConfig(
            model_id="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            provider="cloudflare",
            litellm_model="openai/@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=1,
            api_key_env="CLOUDFLARE_API_KEY",
        ),
        HostedModelConfig(
            model_id="@cf/mistralai/mistral-small-3.1-24b-instruct",
            provider="cloudflare",
            litellm_model="openai/@cf/mistralai/mistral-small-3.1-24b-instruct",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=1,
            api_key_env="CLOUDFLARE_API_KEY",
        ),

        # Cloudflare — Priority 2
        HostedModelConfig(
            model_id="@cf/meta/llama-4-scout-17b-16e-instruct",
            provider="cloudflare",
            litellm_model="openai/@cf/meta/llama-4-scout-17b-16e-instruct",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=2,
            api_key_env="CLOUDFLARE_API_KEY",
        ),
        HostedModelConfig(
            model_id="@cf/google/gemma-4-26b-a4b-it",
            provider="cloudflare",
            litellm_model="openai/@cf/google/gemma-4-26b-a4b-it",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=2,
            api_key_env="CLOUDFLARE_API_KEY",
        ),

        # Cloudflare / Kilo — Priority 3
        HostedModelConfig(
            model_id="@cf/aisingapore/gemma-sea-lion-v4-27b-it",
            provider="cloudflare",
            litellm_model="openai/@cf/aisingapore/gemma-sea-lion-v4-27b-it",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=3,
            api_key_env="CLOUDFLARE_API_KEY",
        ),
        HostedModelConfig(
            model_id="reflection/beam-free",
            provider="kilocode",
            litellm_model="openai/reflection/beam-free",
            max_new_tokens=512,
            capabilities=EVALUATION,
            priority=3,
            api_key_env="KILOCODE_API_KEY",
        ),
    ),

    "guardrail": (
        # Original primary-provider candidates — unchanged
        HostedModelConfig(
            model_id="gemini-3.5-flash-lite",
            provider="google_genai",
            litellm_model="gemini/gemini-3.5-flash-lite",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=1,
            api_key_env="GOOGLE_API_KEY",
        ),
        HostedModelConfig(
            model_id="openai/gpt-oss-20b",
            provider="groq",
            litellm_model="groq/openai/gpt-oss-20b",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=2,
            api_key_env="GROQ_API_KEY",
        ),
        HostedModelConfig(
            model_id="nvidia/nemotron-3.5-bolt-e4b",
            provider="nvidia",
            litellm_model="nvidia_nim/nvidia/nemotron-3.5-bolt-e4b",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=3,
            api_key_env="NVIDIA_API_KEY",
        ),
        HostedModelConfig(
            model_id="qwen/qwen3.8-27b",
            provider="groq",
            litellm_model="groq/qwen/qwen3.8-27b",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=4,
            api_key_env="GROQ_API_KEY",
        ),

        # Cloudflare — Priority 1
        HostedModelConfig(
            model_id="@cf/meta/llama-3.1-8b-instruct-fp8",
            provider="cloudflare",
            litellm_model="openai/@cf/meta/llama-3.1-8b-instruct-fp8",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=1,
            api_key_env="CLOUDFLARE_API_KEY",
        ),
        HostedModelConfig(
            model_id="@cf/mistral/mistral-7b-instruct-v0.2-lora",
            provider="cloudflare",
            litellm_model="openai/@cf/mistral/mistral-7b-instruct-v0.2-lora",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=1,
            api_key_env="CLOUDFLARE_API_KEY",
        ),

        # Cloudflare — Priority 2
        HostedModelConfig(
            model_id="@cf/meta/llama-3.2-3b-instruct",
            provider="cloudflare",
            litellm_model="openai/@cf/meta/llama-3.2-3b-instruct",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=2,
            api_key_env="CLOUDFLARE_API_KEY",
        ),

        # Cloudflare — Priority 3
        HostedModelConfig(
            model_id="@cf/google/gemma-7b-it-lora",
            provider="cloudflare",
            litellm_model="openai/@cf/google/gemma-7b-it-lora",
            max_new_tokens=256,
            capabilities=GUARDRAIL,
            priority=3,
            api_key_env="CLOUDFLARE_API_KEY",
        ),
    ),
}


# ------------------------------------------------------------------
# Local Hugging Face Transformers models
# ------------------------------------------------------------------

@dataclass(frozen=True)
class LocalModelConfig:
    model_id: str
    max_new_tokens: int
    temperature: float = 0.0
    capabilities: frozenset[str] = TEXT
    quantization: str | None = "4bit"
    device_map: str = "auto"
    enabled: bool = True


# ------------------------------------------------------------------
# Optional local Hugging Face configurations
# ------------------------------------------------------------------

LOCAL_MODEL_CONFIGS: dict[ModelRole, LocalModelConfig] = {
    "reasoning": LocalModelConfig(
        model_id="Qwen/Qwen3-8B",
        max_new_tokens=512,
        capabilities=REASONING,
        temperature=0.1,
    ),
    "judge": LocalModelConfig(
        model_id="Qwen/Qwen3-8B",
        max_new_tokens=512,
        capabilities=EVALUATION,
    ),
    "guardrail": LocalModelConfig(
        model_id="Qwen/Qwen3-8B",
        max_new_tokens=256,
        capabilities=GUARDRAIL,
    ),
}


# ------------------------------------------------------------------
# Role requirements
# ------------------------------------------------------------------

ROLE_REQUIREMENTS: dict[ModelRole, frozenset[str]] = {
    "reasoning": REASONING,
    "judge": EVALUATION,
    "guardrail": GUARDRAIL,
}


# Stable LiteLLM Router aliases for each role.
LITELLM_MODEL_GROUPS: dict[ModelRole, str] = {
    "reasoning": "quantpilot-reasoning",
    "judge": "quantpilot-judge",
    "guardrail": "quantpilot-guardrail",
}


# Preferred hosted configuration per role.
MODEL_CONFIGS: dict[ModelRole, HostedModelConfig] = {
    role: min(candidates, key=lambda config: config.priority)
    for role, candidates in MODEL_CANDIDATES.items()
}


# ------------------------------------------------------------------
# Hosted model selection
# ------------------------------------------------------------------

def select_model_config(
    role: ModelRole,
    required_capabilities: frozenset[str] = frozenset(),
) -> HostedModelConfig:
    required = ROLE_REQUIREMENTS[role] | required_capabilities

    compatible = [
        config
        for config in MODEL_CANDIDATES[role]
        if config.enabled and required.issubset(config.capabilities)
    ]

    if not compatible:
        raise ValueError(
            f"No compatible enabled hosted model for role '{role}', "
            f"required capabilities: {sorted(required)}"
        )

    return min(compatible, key=lambda config: config.priority)


# ------------------------------------------------------------------
# Local Hugging Face model selection
# ------------------------------------------------------------------

def select_local_model_config(
    role: ModelRole,
    required_capabilities: frozenset[str] = frozenset(),
):
    required = ROLE_REQUIREMENTS[role] | required_capabilities
    config = LOCAL_MODEL_CONFIGS.get(role)

    if (
        config is None
        or not config.enabled
        or not required.issubset(config.capabilities)
    ):
        raise ValueError(
            f"No compatible enabled local model for role '{role}', "
            f"required capabilities: {sorted(required)}"
        )

    return config
