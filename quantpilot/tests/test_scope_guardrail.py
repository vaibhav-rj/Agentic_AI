from src.guardrails.scope import validate_research_scope

from unittest.mock import patch, Mock
from src.guardrails.scope import validate_research_scope
import pytest

'''
def main():
    # In scope
    result = validate_research_scope(
        "Analyze Apple's historical volatility."
    )
    print(result)

    # Another valid query
    result = validate_research_scope(
        "Compare revenue growth and valuation."
    )
    print(result)

    # Out of scope
    try:
        validate_research_scope(
            "Explain how to bake a chocolate cake."
        )
    except ValueError as e:
        print("Out-of-scope query rejected:", e)


if __name__ == "__main__":
    main()
'''

#standalone LLM mock:=

#+ve cases
@patch("src.guardrails.scope.invoke_with_fallback")#temporarily replaces the real LLM gateway function with a mock
def test_unrecognized_finance_query_accepted_by_llm(mock_invoke):
    mock_invoke.return_value = Mock(
        content='{"in_scope": true}'#simulates the LLM's response; no model is called.
    )

    result = validate_research_scope("Explain enterprise value to EBITDA multiples")#runs normally

    assert result.in_scope is True
    assert result.reason == "Query accepted by the semantic scope classifier."
    mock_invoke.assert_called_once()

#-ve cases(python -m pytest tests/test_scope_guardrail.py::test_unrelated_query_rejected_by_llm -q/m)
# ===>brackted portion for 1-by-1 test
@patch("src.guardrails.scope.invoke_with_fallback")
def test_unrelated_query_rejected_by_llm(mock_invoke):
    mock_invoke.return_value = Mock(
        content='{"in_scope": false}'
    )

    with pytest.raises(
        ValueError,
        match="outside QuantPilot's financial and market research scope",
    ):
        validate_research_scope("Explain the history of ancient Rome")

    mock_invoke.assert_called_once()

#Fail closed if the classifier fails
@patch("src.guardrails.scope.invoke_with_fallback")
def test_classifier_failure_rejected(mock_invoke):
    mock_invoke.side_effect = RuntimeError("Classifier unavailable")

    with pytest.raises(
        ValueError,
        match="Unable to verify research scope",
    ):
        validate_research_scope("Explain enterprise value to EBITDA multiples")

    mock_invoke.assert_called_once()

def test_recognized_finance_query_bypasses_llm():
    with patch("src.guardrails.scope.invoke_with_fallback") as mock_invoke:
        result = validate_research_scope(
            "Analyze Apple's historical volatility."
        )

    assert result.in_scope is True
    mock_invoke.assert_not_called()