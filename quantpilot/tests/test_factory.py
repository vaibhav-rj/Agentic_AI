from unittest.mock import MagicMock, patch

from src.llm.factory import invoke_with_fallback


@patch("src.llm.factory.get_litellm_model")
@patch("src.llm.factory._sanitize_messages")
def test_hosted_invokes_gateway_once(mock_sanitize, mock_get_model):
    messages = [{"role": "user", "content": "test"}]
    sanitized = [{"role": "user", "content": "sanitized"}]

    mock_sanitize.return_value = sanitized

    mock_response = MagicMock()
    mock_response.response_metadata = {"model_id": "reasoning-1-0"}

    mock_model = MagicMock()
    mock_model.invoke.return_value = mock_response
    mock_get_model.return_value = mock_model

    result = invoke_with_fallback(
        role="reasoning",
        messages=messages,
        required_capabilities=frozenset({"reasoning"}),
        backend="hosted",
    )

    mock_sanitize.assert_called_once_with(messages)
    mock_get_model.assert_called_once_with(
        "reasoning", frozenset({"reasoning"})
    )
    mock_model.invoke.assert_called_once_with(sanitized)
    assert result is mock_response


@patch("src.llm.factory.get_litellm_model")
@patch("src.llm.factory._sanitize_messages")
def test_hosted_exception_propagates(mock_sanitize, mock_get_model):
    mock_sanitize.return_value = [{"role": "user", "content": "test"}]

    mock_model = MagicMock()
    mock_model.invoke.side_effect = RuntimeError("Provider failure")
    mock_get_model.return_value = mock_model

    try:
        invoke_with_fallback(
            role="reasoning",
            messages=[{"role": "user", "content": "test"}],
            backend="hosted",
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert str(exc) == "Provider failure"

    mock_get_model.assert_called_once()
    mock_model.invoke.assert_called_once()