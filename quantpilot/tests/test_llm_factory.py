from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from src.llm import factory
from typing import Any

from src.llm.config import ModelRole

captured: dict[str, Any] = {}


# ---------------------------------------------------------------------
# 1. Message sanitization: strings, LangChain messages, and text blocks
# ---------------------------------------------------------------------

def test_sanitize_plain_string():
    result = factory._sanitize_messages("Contact user@example.com")

    assert "user@example.com" not in result
    assert "[EMAIL REDACTED]" in result


def test_sanitize_message_object_preserves_role():
    message = HumanMessage(content="Contact user@example.com")

    result = factory._sanitize_messages([message])

    assert isinstance(result[0], HumanMessage)
    assert result[0].type == "human"
    assert "user@example.com" not in result[0].content
    assert "[EMAIL REDACTED]" in result[0].content


def test_sanitize_content_blocks_preserves_other_blocks():

    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": "Contact user@example.com"},
                {"type": "image", "url": "image-placeholder"},
            ]
        )
    ]

    result = factory._sanitize_messages(messages)
    blocks = result[0].content

    assert "user@example.com" not in blocks[0]["text"]
    assert "[EMAIL REDACTED]" in blocks[0]["text"]
    assert blocks[1] == {"type": "image", "url": "image-placeholder"}


# ---------------------------------------------------------------------
# 2. Load balancing: eligible-candidate filtering and empty candidates
# ---------------------------------------------------------------------

#monkeypatch is a pytest fixture used to temporarily replace attributes or functions during a test,
def test_select_load_balanced_model_filters_incompatible_candidates(monkeypatch):
    role: ModelRole = 'reasoning'#can use any of the LiterEval of ModelRole

    eligible = SimpleNamespace(
        enabled=True,
        capabilities=frozenset({"text"}),
        load_weight=1,
        priority=1,
    )
    ineligible = SimpleNamespace(
        enabled=True,
        capabilities=frozenset(),
        load_weight=1,
        priority=2,
    )

    monkeypatch.setattr(
        factory, "MODEL_CANDIDATES", {role: [eligible, ineligible]}
    )
    monkeypatch.setattr(
        factory, "ROLE_REQUIREMENTS", {role: frozenset({"text"})}
    )

    #random selection based on candidate model config selceted whose capablities are superset of the given role's requiremnt 
    result = factory.select_load_balanced_model(role)

    assert result is eligible


def test_select_load_balanced_model_raises_when_no_candidates(monkeypatch):
    role: ModelRole = 'reasoning'#can use any of the LiterEval of ModelRole

    #no model selected
    monkeypatch.setattr(factory, "MODEL_CANDIDATES", {role: []})

    with pytest.raises(ValueError, match="No compatible model candidates"):
        factory.select_load_balanced_model(role)


# ---------------------------------------------------------------------
# 3. Gateway integration: PII must be sanitized before model invocation
# ---------------------------------------------------------------------

def test_invoke_with_fallback_sanitizes_before_model_call(monkeypatch):
    role: ModelRole = 'guardrail'#can use any of the LiterEval of ModelRole

    config = SimpleNamespace(
        provider="test",
        model_id="test-model",
        enabled=True,
        capabilities=frozenset(),
        load_weight=1,
        priority=1,
    )

    captured = {}
    model = Mock()
    #makes the mocked model raise an error when invoked
    model.invoke.side_effect = lambda messages: (
        captured.update(messages=messages) or "mock result"
    )

    #here *a, **k returns the test's predefined config mocking eal selection function
    monkeypatch.setattr(
        factory, "select_load_balanced_model", lambda *a, **k: config
    )
    monkeypatch.setattr(factory, "_build_model", lambda selected: model)
    monkeypatch.setattr(factory, "MODEL_CANDIDATES", {role: [config]})
    monkeypatch.setattr(factory, "ROLE_REQUIREMENTS", {role: frozenset()})

    factory.invoke_with_fallback(
        role,
        [HumanMessage(content="Contact user@example.com")],
    )

    invoked_messages = captured["messages"]
    assert "user@example.com" not in invoked_messages[0].content
    assert "[EMAIL REDACTED]" in invoked_messages[0].content


# ---------------------------------------------------------------------
# 4. Fallback: move to the next candidate when the first model fails
# ---------------------------------------------------------------------

def test_invoke_with_fallback_uses_next_candidate(monkeypatch):
    role: ModelRole = 'fast'#can use any of the LiterEval of ModelRole

    first = SimpleNamespace(
        provider="test",
        model_id="first",
        enabled=True,
        capabilities=frozenset(),
        load_weight=1,
        priority=1,
    )
    second = SimpleNamespace(
        provider="test",
        model_id="second",
        enabled=True,
        capabilities=frozenset(),
        load_weight=1,
        priority=2,
    )

    first_model = Mock()
    first_model.invoke.side_effect = RuntimeError("simulated failure")#first model invokes sid eeffect
    second_model = Mock()
    second_model.invoke.return_value = "success"#2nd model invokes success

    monkeypatch.setattr(
        factory, "select_load_balanced_model", lambda *a, **k: first
    )
    monkeypatch.setattr(
        factory, "MODEL_CANDIDATES", {role: [first, second]}
    )
    monkeypatch.setattr(factory, "ROLE_REQUIREMENTS", {role: frozenset()})
    monkeypatch.setattr(
        factory,
        "_build_model",
        lambda config: first_model if config is first else second_model,
    )#selects the 1st model if 'config' present else second model

    result = factory.invoke_with_fallback(role, ["test message"])

    assert result == "success"
    first_model.invoke.assert_called_once()
    second_model.invoke.assert_called_once()


# ---------------------------------------------------------------------
# 5. Failure handling: report an error when every model fails
# ---------------------------------------------------------------------

def test_invoke_with_fallback_raises_when_all_candidates_fail(monkeypatch):
    role: ModelRole = 'fast'#can use any of the LiterEval of ModelRole
    config = SimpleNamespace(
        provider="test",
        model_id="broken",
        enabled=True,
        capabilities=frozenset(),
        load_weight=1,
        priority=1,
    )

    model = Mock()
    model.invoke.side_effect = RuntimeError("simulated failure")

    monkeypatch.setattr(
        factory, "select_load_balanced_model", lambda *a, **k: config
    )
    monkeypatch.setattr(factory, "MODEL_CANDIDATES", {role: [config]})
    monkeypatch.setattr(factory, "ROLE_REQUIREMENTS", {role: frozenset()})
    monkeypatch.setattr(factory, "_build_model", lambda selected: model)

    with pytest.raises(RuntimeError, match="All model candidates failed"):
        factory.invoke_with_fallback(role, ["test message"])