#from functools import lru_cache
from typing import Any, Literal
import gc
import torch
import re

import logging

logger = logging.getLogger(__name__)

from langchain_core.language_models import BaseChatModel

from .config import (
    MODEL_CANDIDATES,
    ROLE_REQUIREMENTS,
    LocalModelConfig,
    HostedModelConfig,
    ModelRole,
    select_local_model_config,
)
from .providers.huggingface import build_huggingface_chat_model
from .litellm_gateway import get_litellm_model

Backend = Literal["hosted", "huggingface"]

def get_model(
    role: ModelRole,
    backend: Backend = "hosted",
) -> BaseChatModel:
    """Return a hosted LiteLLM Router model or local HF model."""

    if backend == "hosted":
        return get_litellm_model(role)

    if backend == "huggingface":
        config = select_local_model_config(role)
        return _build_model(config)

    raise ValueError(f"Unsupported model backend: {backend}")


def _build_model(config: LocalModelConfig) -> BaseChatModel:
    """Build a local Hugging Face Transformers model."""

    if not config.enabled:
        raise ValueError(f"Local model is disabled: {config.model_id}")

    return build_huggingface_chat_model(
        model_id=config.model_id,
        temperature=config.temperature,
        max_new_tokens=config.max_new_tokens,
    )



def sanitize_content(content: Any) -> Any:
    """Redact personally identifiable information from supported content."""
    from src.guardrails.pii import redact_pii

    if isinstance(content, str):
        return redact_pii(content)

    if isinstance(content, list):
        sanitized = []
        for block in content:
            if isinstance(block, dict):
                block = block.copy()
                if isinstance(block.get("text"), str):
                    block["text"] = redact_pii(block["text"])
            sanitized.append(block)
        return sanitized

    return content


def _sanitize_messages(messages: Any) -> Any:
    """Sanitize message content before passing it to a model."""
    from src.guardrails.pii import redact_pii

    if isinstance(messages, str):
        return redact_pii(messages)

    if hasattr(messages, "content"):
        return messages.model_copy(
            update={"content": sanitize_content(messages.content)}
        )

    sanitized_messages = []
    for message in messages:
        if isinstance(message, dict):
            message = message.copy()
            if "content" in message:
                message["content"] = sanitize_content(message["content"])
        elif hasattr(message, "content"):
            message = message.model_copy(
                update={"content": sanitize_content(message.content)}
            )
        sanitized_messages.append(message)

    return sanitized_messages

'''
def _compatible_candidates(
    role: ModelRole,
    required_capabilities: frozenset[str] = frozenset(),
) -> list[HostedModelConfig]:
    """Return compatible hosted candidates in priority order."""

    required = ROLE_REQUIREMENTS.get(role, frozenset()) | required_capabilities

    candidates = [
        config
        for config in MODEL_CANDIDATES.get(role, ())
        if config.enabled
        and required.issubset(config.capabilities)
    ]

    return sorted(candidates, key=lambda config: config.priority)
'''
def normalize_response(response):
    content = getattr(response, "content", None)

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Empty or invalid LLM response")

    # Remove reasoning trace, if present.
    content = re.sub(
        r"^.*?</think>|^.*?<think\s*>", #r"^.*?<\/think\s*>",
        "",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove surrounding Markdown code fences.
    content = re.sub(
        r"^\s*```(?:json)?\s*|\s*```\s*$",
        "",
        content,
        flags=re.IGNORECASE,
    ).strip()

    if not content:
        raise ValueError("Empty response after normalization")

    if content != response.content:
        response = response.model_copy(update={"content": content})

    return response

def invoke_with_fallback(
    role: ModelRole,
    messages: Any,
    required_capabilities: frozenset[str] = frozenset(),
    backend: Backend = "hosted",
):
    """Invoke via LiteLLM fallback or the explicitly selected local backend."""

    sanitized_messages = _sanitize_messages(messages)

    logger.info("LLM invocation started | role=%s | backend=hosted", role)
    if backend == "hosted":

         # ChatLiteLLMRouter exposes the selected deployment metadata here.
        try:
            model = get_litellm_model(role, required_capabilities)

            response =model.invoke(sanitized_messages)

            response = normalize_response(response)
            logger.info("Hosted LLM invocation completed | role=%s", role)

            #logger.info("LiteLLM deployment used: %s", getattr(response, "hidden_params", {}).get("model_id", "unknown")) 
            logger.info("LiteLLM deployment used: %s", response.response_metadata.get("model_id", "unknown"))# LiteLLM adapter--->
            
            # cahtLiteLLM-->exposes deployment metadata inside response.response_metadata, including model_id(whaeras earlier we 
            # thought it at native respinse level(which is apt forLiteLLM. router not ).

            return(response)
        except Exception as exc:
            #logger.warning("Could not read LiteLLM deployment metadata: %s",exc,)
            logger.exception("Hosted LLM invocation failed | role=%s", role)
            raise


    if backend == "huggingface":
        config = select_local_model_config(
            role, required_capabilities
        )

        try:
            #print(f"[LLM Factory] Backend: HuggingFace | Model: {config.model_id}")
            logger.info("LLM invocation started | role=%s | backend=huggingface | model=%s", role, config.model_id)
            return _build_model(config).invoke(sanitized_messages)

        except Exception as exc:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            raise RuntimeError(
                f"Local Hugging Face model failed for role '{role}': {exc}"
            ) from exc

    raise ValueError(f"Unsupported model backend: {backend}")

