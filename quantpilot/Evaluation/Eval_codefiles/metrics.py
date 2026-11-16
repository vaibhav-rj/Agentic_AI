
from __future__ import annotations

import re
from collections import Counter
from typing import Any


def _dict(value: Any) -> dict:
    """Normalize optional state values without allowing malformed shapes to break a run."""
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    """Normalize optional list fields from partially completed workflow states."""
    return value if isinstance(value, list) else []


def _norm(value: Any) -> str:
    """Normalize text for conservative exact-identity comparisons."""
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _evidence_key(item: dict) -> tuple[str, str, str]:
    """Build the evaluation's exact normalized duplicate key (not semantic deduplication)."""
    claim = _norm(item.get("claim"))
    evidence = _norm(item.get("evidence"))
    source = _norm(item.get("source"))
    # Prefer source + factual payload so repeated copies across task types are grouped.
    return source, evidence, claim


def evaluate_run(initial: dict, final: dict | None, log_text: str, run_id: str) -> dict:
    """Extract one run's observable workflow, evidence, adjudication, and report metrics."""
    state = final or {}
    rq = _dict(state.get("research_query"))
    plan = _dict(state.get("research_plan"))
    replan = _dict(state.get("replan_plan"))
    results = _list(state.get("research_results"))
    evidence = _list(_dict(state.get("evidence")).get("items"))
    thesis = _dict(state.get("thesis"))
    critique = _dict(state.get("critique"))
    adjudication = _dict(state.get("adjudication"))
    report = _dict(state.get("final_report"))
    steps = _list(plan.get("steps"))
    replan_steps = _list(replan.get("steps"))
    analyzer_task_types = {str(x) for x in _list(rq.get("task_types"))}
    planned_task_types = {str(s.get("task_type")) for s in steps if isinstance(s, dict)}

    required_steps = [s for s in steps if isinstance(s, dict) and s.get("required", True)]
    planned_categories = {str(s.get("tool_category")) for s in required_steps}
    executed_categories = {str(r.get("tool_category")) for r in results if isinstance(r, dict) and not r.get("error")}
    successful_results = [r for r in results if isinstance(r, dict) and not r.get("error") and r.get("result") is not None]
    failed_results = [r for r in results if isinstance(r, dict) and (r.get("error") or r.get("status") == "error")]
    statuses = Counter(str(e.get("status", "UNKNOWN")).upper() for e in evidence if isinstance(e, dict))
    evidence_keys = [_evidence_key(e) for e in evidence if isinstance(e, dict)]
    duplicate_count = len(evidence_keys) - len(set(evidence_keys))
    sources = {str(e.get("source")) for e in evidence if isinstance(e, dict) and e.get("source")}

    # Match the adjudicator's exact distinct-evidence/debt calculation.
    adjudicator_evidence_keys = {
        (e.get("claim"), e.get("source_type"), e.get("source"), e.get("evidence"))
        for e in evidence if isinstance(e, dict)
    }
    evidence_debt = _list(adjudication.get("evidence_debt"))
    distinct_evidence_debt = {
        str(item).strip().casefold() for item in evidence_debt if str(item).strip()
    }

    decision = str(adjudication.get("decision", "NOT_REACHED")).upper()
    quality_band = str(adjudication.get("quality_band", "NOT_RECORDED")).upper()
    outcome_map = {
        ("FAIL", "FAILED"): "FULLY_FAILED",
        ("FAIL", "AVERAGE"): "PARTIAL_PASS",
        ("FAIL", "FAIRLY_PASSED"): "FAIRLY_PASSED",
        ("FAIL", "STRONGLY_PASSED"): "STRONGLY_PASSED",
    }
    evaluation_outcome = (
        "FULLY_PASSED" if decision == "PASS"
        else outcome_map.get((decision, quality_band), "REVIEW_REQUIRED")
    )
    log_lower = log_text.lower()
    input_rejected = bool(re.search(r"Node failed: input_guardrails|outside QuantPilot|must not be empty|ensure this value has at least|ensure this value has at most", log_text, re.I))
    input_accepted = bool(re.search(r"Research scope accepted|Node completed: input_guardrails", log_text, re.I)) and not input_rejected
    input_node_started = bool(re.search(r"Node started: input_guardrails", log_text, re.I))
    pii_redacted = bool(re.search(r"PII/confidential content detected and redacted", log_text, re.I))
    output_issue_match = re.search(r"FinalReport guardrail issues:\s*(.+)", log_text)
    output_unverified_match = re.search(r"Output review unverified:\s*(.+)", log_text)
    validation_remarks = str(report.get("validation_remarks", "")).strip().upper()
    if not output_issue_match and validation_remarks.startswith("ISSUES_FOUND:"):
        output_issue_match = True
    if not output_unverified_match and validation_remarks.startswith("UNVERIFIED:"):
        output_unverified_match = True

    # An explicit node failure outranks review remarks; an incomplete LLM review is UNVERIFIED,
    # not a pass merely because the surrounding workflow reached completion.
    output_guardrail_failed = bool(re.search(r"Node failed: output_guardrail", log_text, re.I))
    output_guardrail_completed = bool(re.search(r"Node completed: output_guardrail", log_text, re.I))
    if output_guardrail_failed:
        output_guardrail_status = "FAILED"
    elif output_unverified_match:
        output_guardrail_status = "UNVERIFIED"
    elif output_issue_match:
        output_guardrail_status = "ISSUES_FOUND"
    elif output_guardrail_completed:
        output_guardrail_status = "PASS_LOGGED"
    else:
        output_guardrail_status = "NOT_OBSERVED"

    node_durations = [float(x) for x in re.findall(r"Node completed: .*?duration=([0-9.]+)s", log_text)]
    total_duration = round(sum(node_durations), 3) if node_durations else None
    llm_calls = len(re.findall(r"LLM invocation started", log_text, re.I))
    fallback_events = len(re.findall(r"Falling back to model_group|fallback.*model|fallback used", log_text, re.I))
    exceptions = len(re.findall(r"\b(ERROR|Traceback|Exception|Error):", log_text))
    graph_nodes = re.findall(r"Node completed: ([^|\n]+?)\s*(?:\||$)", log_text, re.M)

    # Final-report checks below are structural/cross-stage consistency checks, not fact verification.
    has_final = bool(report)
    has_final_schema = all(k in report for k in ("user_query", "summary", "thesis", "conclusion", "confidence", "normalized_results", "limitations"))
    report_limitations = _list(report.get("limitations"))
    report_limitation_set = {str(x).strip().casefold() for x in report_limitations if str(x).strip()}
    debt_set = {str(x).strip().casefold() for x in evidence_debt if str(x).strip()}
    report_confidence = report.get("confidence")
    adjudication_confidence = adjudication.get("confidence")
    thesis_text = str(thesis.get("thesis", "")).strip()
    critique_text = str(critique.get("critique", "")).strip()
    thesis_confidence = thesis.get("confidence")
    critique_confidence = critique.get("confidence")
    thesis_confidence_valid = isinstance(thesis_confidence, (int, float)) and not isinstance(thesis_confidence, bool) and 0 <= thesis_confidence <= 1
    critique_confidence_valid = isinstance(critique_confidence, (int, float)) and not isinstance(critique_confidence, bool) and 0 <= critique_confidence <= 1
    critique_flags = [str(x).strip().casefold() for x in _list(critique.get("missing_evidence")) + _list(critique.get("challenged_evidence")) if str(x).strip()]
    debt_norm = {str(x).strip().casefold() for x in evidence_debt if str(x).strip()}
    critique_flags_covered_by_debt = set(critique_flags).issubset(debt_norm)
    decision_debt_consistent = (decision == "FAIL" and bool(evidence_debt)) or (decision == "PASS" and not evidence_debt) or decision == "NOT_REACHED"
    adjudication_rationale = str(adjudication.get("rationale", "")).strip()
    run_failed = bool(re.search(r"Node failed:", log_text, re.I))

    return {
        "run_id": run_id,
        "user_query": state.get("user_query") or initial.get("user_query", ""),
        "terminal_state": "FINAL_REPORT" if has_final else ("GUARDRAIL_REJECTED" if input_rejected else "INCOMPLETE_OR_FAILED"),
        "input_guardrail": "REJECTED" if input_rejected else ("ACCEPTED" if input_accepted else "NOT_OBSERVED"),
        "input_query_raw_length": len(str(initial.get("user_query", state.get("user_query", "")))),
        "input_query_length_within_bounds": 5 <= len(str(initial.get("user_query", state.get("user_query", "")).strip())) <= 2000,
        "input_guardrail_node_started": input_node_started,
        "input_guardrail_node_completed": bool(re.search(r"Node completed: input_guardrails", log_text, re.I)),
        "input_guardrail_scope_accepted": bool(re.search(r"Research scope accepted", log_text, re.I)),
        "input_guardrail_failure_signal": input_rejected,
        "pii_redaction_observed": pii_redacted,
        "query_analyzer_task_types": ";".join(sorted(analyzer_task_types)),
        "query_analyzer_entities": ";".join(map(str, _list(rq.get("entities")))),
        "planned_task_types": ";".join(sorted(planned_task_types)),
        "query_plan_task_type_coverage": round(len(analyzer_task_types & planned_task_types) / len(analyzer_task_types), 3) if analyzer_task_types else None,
        "query_task_types_missing_from_plan": ";".join(sorted(analyzer_task_types - planned_task_types)),
        "plan_task_types_not_in_analyzer": ";".join(sorted(planned_task_types - analyzer_task_types)),
        "planned_required_steps": len(required_steps),
        "planned_tool_categories": ";".join(sorted(planned_categories)),
        "executed_tool_categories": ";".join(sorted(executed_categories)),
        "required_category_coverage": round(len(planned_categories & executed_categories) / len(planned_categories), 3) if planned_categories else None,
        "research_result_count": len(results),
        "successful_result_count": len(successful_results),
        "failed_result_count": len(failed_results),
        "replan_count": int(state.get("replan_count", 0) or 0),
        "replan_step_count": len(replan_steps),
        "evidence_count": len(evidence),
        "evidence_supported": statuses.get("SUPPORTED", 0),
        "evidence_partially_supported": statuses.get("PARTIALLY_SUPPORTED", 0),
        "evidence_unsupported": statuses.get("UNSUPPORTED", 0),
        "evidence_conflicting": statuses.get("CONFLICTING", 0),
        "evidence_unverified": statuses.get("UNVERIFIED", 0),
        "evidence_challenged_legacy_alias": statuses.get("CHALLENGED", 0),
        "evidence_other_status": sum(v for k, v in statuses.items() if k not in {"SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONFLICTING", "UNVERIFIED", "CHALLENGED"}),
        "evidence_unique_source_count": len(sources),
        "adjudicator_distinct_evidence_count": len(adjudicator_evidence_keys),
        "adjudicator_duplicate_evidence_count": len(evidence) - len(adjudicator_evidence_keys),
        "exact_evidence_duplicate_count": duplicate_count,
        "thesis_text_for_review": thesis_text,
        "critique_text_for_review": critique_text,
        "adjudication_rationale_for_review": adjudication_rationale,
        "thesis_present": bool(thesis_text),
        "thesis_confidence": thesis_confidence,
        "thesis_confidence_valid_range": thesis_confidence_valid,
        "thesis_confidence_content_review": "NOT_INDEPENDENTLY_CALIBRATED" if thesis_text and thesis_confidence_valid else "INVALID_OR_MISSING",
        "critique_present": bool(critique_text),
        "critique_confidence": critique_confidence,
        "critique_confidence_valid_range": critique_confidence_valid,
        "critique_confidence_content_review": "NOT_INDEPENDENTLY_CALIBRATED" if critique_text and critique_confidence_valid else "INVALID_OR_MISSING",
        "critique_deterministic_flags_covered_by_adjudication_debt": critique_flags_covered_by_debt,
        "adjudication_decision_consistent_with_debt": decision_debt_consistent,
        "adjudication_rationale_present": bool(adjudication_rationale),
        "adjudication_rationale_semantic_alignment": "NOT_INDEPENDENTLY_ASSESSED" if adjudication_rationale else "MISSING",
        "challenged_evidence_count": len(_list(critique.get("challenged_evidence"))),
        "missing_evidence_count": len(_list(critique.get("missing_evidence"))),
        "adjudication_decision": decision,
        "adjudication_quality_band": quality_band,
        "evaluation_outcome": evaluation_outcome,
        "adjudication_confidence": adjudication.get("confidence"),
        "adjudication_quality_score": adjudication.get("quality_score"),
        "evidence_debt_count": len(evidence_debt),
        "adjudicator_distinct_evidence_debt_count": len(distinct_evidence_debt),
        "missing_tools_count": len(_list(adjudication.get("missing_tools"))),
        "final_report_present": has_final,
        "final_report_schema_complete": has_final_schema,
        "final_report_summary_present": bool(str(report.get("summary", "")).strip()),
        "final_report_thesis_present": bool(str(report.get("thesis", "")).strip()),
        "final_report_conclusion_present": bool(str(report.get("conclusion", "")).strip()),
        "final_report_thesis_consistent_with_generator": bool(thesis) and report.get("thesis") == thesis.get("thesis"),
        "final_report_confidence_matches_adjudication": isinstance(report_confidence, (int, float)) and isinstance(adjudication_confidence, (int, float)) and abs(report_confidence - adjudication_confidence) < 1e-9,
        "final_report_confidence": report_confidence,
        "final_report_normalized_result_count": len(_list(report.get("normalized_results"))),
        "final_report_limitation_count": len(report_limitations),
        "final_report_discloses_all_adjudication_debt": debt_set.issubset(report_limitation_set),
        "final_report_limitations_match_adjudication_debt": debt_set == report_limitation_set,
        "output_guardrail_status": output_guardrail_status,
        "output_guardrail_node_completed": output_guardrail_completed,
        "output_guardrail_review_issues_logged": bool(output_issue_match),
        "output_guardrail_review_unverified": bool(output_unverified_match),
        "output_guardrail_validation_remarks": str(report.get("validation_remarks", "")),
        "run_failed_log_signal": run_failed,
        "logged_node_completion_count": len(graph_nodes),
        "logged_node_duration_sum_seconds": total_duration,
        "llm_invocation_count": llm_calls,
        "logged_fallback_event_count": fallback_events,
        "logged_exception_signal_count": exceptions,
    }
