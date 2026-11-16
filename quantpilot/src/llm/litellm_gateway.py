
import os
from functools import lru_cache
from .config import resolve_api_base

import logging

logger = logging.getLogger(__name__)

from .config import (
    MODEL_CANDIDATES,
    LITELLM_MODEL_GROUPS,
    ROLE_REQUIREMENTS,
    ModelRole,
)


def _build_model_list(role: ModelRole, required_capabilities=frozenset()):
    '''Build eligible LiteLLM deployments, grouped by priority.'''

    required = ROLE_REQUIREMENTS[role] | required_capabilities
    deployments = []
    missing_keys = []
    usable_candidates = []


    # Retain only enabled, capability-compatible candidates.
    # Lower priority numbers are tried before higher ones.
    candidates = sorted(
        (
            config
            for config in MODEL_CANDIDATES[role]
            if config.enabled
            and required.issubset(config.capabilities)
        ),
        key=lambda config: config.priority,
    )


    # Generate a unique index separately inside each priority group.
    # Example: priority 1 -> 0, 1, 2; priority 2 -> 0, 1.
    priority_indexes = {}#added later

    for config in candidates:
        api_key = os.getenv(config.api_key_env) if config.api_key_env else None

        if not api_key:
            missing_keys.append(config.api_key_env or "API key not configured")
            continue

        priority = config.priority
        index = priority_indexes.get(priority, 0)
        priority_indexes[priority] = index + 1

        litellm_params = {
            "model": config.litellm_model,
            "api_key": api_key,

            # LiteLLM uses this value for order-based priority fallback.
            "order": config.priority,

            # Keep generation settings specific to each deployment.
            "max_tokens": config.max_new_tokens,
            "temperature": config.temperature,
        }

        # Resolve provider-specific API endpoints when required.
        api_base = resolve_api_base(config.provider)

        if api_base:
            litellm_params["api_base"] = api_base

        deployments.append({
            # All deployments for a role share one Router model group.
            "model_name": LITELLM_MODEL_GROUPS[role],
            "litellm_params": litellm_params,

            # ID is for tracing; provider is for diagnostics.
            "model_info": {
                "id": f"{role}-{priority}-{index}",
                "provider": config.provider,
            },
        })

        '''
        deployments.append({
            "model_name": LITELLM_MODEL_GROUPS[role],
            "litellm_params": {
                "model": config.litellm_model,
                "api_key": api_key,
                "order": config.priority,
                "max_tokens": config.max_new_tokens,
                "temperature": config.temperature,
            },
            "model_info": {
                "id": f"{role}-{config.priority}-{config.provider}"
            },
        })
        '''
        usable_candidates.append(config)

    if not deployments:
        raise EnvironmentError(
            f"No usable LiteLLM deployments for '{role}'. "
            f"Check provider API keys: {missing_keys}"
        )

    return deployments, usable_candidates


@lru_cache(maxsize=12)
def get_litellm_model(
    role: ModelRole,
    required_capabilities=frozenset(),
):
    """
    Return a LangChain-compatible LiteLLM Router model.

    LiteLLM handles ordered fallback and response caching.
    """

    from litellm.router import Router
    from langchain_litellm import ChatLiteLLMRouter

    deployments, usable_candidates = _build_model_list(
        role, required_capabilities
    )

    # First usable candidate is the primary deployment by priority.

    '''
    primary = next(
        config
        for config in candidates
        if any(
            deployment["model_info"]["id"]
            == f"{role}-{config.priority}-{config.provider}"
            for deployment in deployments
        )
    )
    '''
    # First usable candidate is the primary deployment by priority.
    primary= usable_candidates[0]

    router_kwargs = {
        "model_list": deployments,

        # Load balancing among eligible deployments.
        "routing_strategy": "simple-shuffle",

        # Initial retry/cooldown settings; verify actual attempt behaviour
        # with the focused Router tests before treating these as final.
        "num_retries": 0,
        "cooldown_time": 5,

        # Disable weighted intra-group failover.
        "enable_weighted_failover": False,

        # Enable LiteLLM response caching.
        "cache_responses": True,
    }    

    # Optional shared persistent cache.
    redis_url = os.getenv("LITELLM_REDIS_URL")
    if redis_url:
        router_kwargs["redis_url"] = redis_url

    '''
    print(
        f"[LLM Gateway] Role: {role} | "
        f"Primary model: {primary.provider}:{primary.model_id} | "
        f"Priority: {primary.priority}"
    )
    '''
    logger.info(
        "Initializing LiteLLM gateway | role=%s | primary=%s:%s | priority=%s",
        role, primary.provider, primary.model_id, primary.priority
    )

    router = Router(**router_kwargs)

    # Per-deployment generation settings are supplied in model_list.
    return ChatLiteLLMRouter(
        router=router,
        model_name=LITELLM_MODEL_GROUPS[role],
        #temperature=primary.temperature,
        #max_tokens=primary.max_new_tokens,
        streaming=False,
    )
