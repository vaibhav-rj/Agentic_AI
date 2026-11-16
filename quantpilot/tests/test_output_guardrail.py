import json
from types import SimpleNamespace

from src.guardrails import output


def make_report():
    from src.schemas.final_report import FinalReport

    return FinalReport(
        user_query="Compare Apple's returns and valuation.",
        summary="Apple showed positive returns.",
        thesis="Apple's performance merits further evaluation.",
        conclusion="Available evidence supports this assessment with limitations.",
        confidence=0.8,
        normalized_results=[{"tool_category": "market", "result": {"returns": 0.1}}],
        limitations=[],
    )


def test_valid_report_returned_unchanged(monkeypatch):
    report = make_report()
    monkeypatch.setattr(
        output, "invoke_with_fallback",
        lambda *args: SimpleNamespace(content='{"issues": []}'),
    )

    assert output.validate_final_report(report) is report


def test_llm_issues_logged_report_preserved(monkeypatch, caplog):
    report = make_report()
    monkeypatch.setattr(
        output, "invoke_with_fallback",
        lambda *args: SimpleNamespace(
            content=json.dumps({"issues": ["Potential unsupported claim"]})
        ),
    )

    assert output.validate_final_report(report) is report
    assert "Potential unsupported claim" in caplog.text


def test_llm_failure_propagates(monkeypatch):
    report = make_report()

    def fail(*args):
        raise RuntimeError("Simulated LLM failure")

    monkeypatch.setattr(output, "invoke_with_fallback", fail)

    import pytest
    with pytest.raises(RuntimeError, match="Simulated LLM failure"):
        output.validate_final_report(report)