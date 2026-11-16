from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .metrics import evaluate_run
except ImportError:
    from metrics import evaluate_run


def read_json(path: Path) -> dict:
    """Load a saved state artifact; malformed or absent files remain non-fatal."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_runs(root: Path) -> list[dict[str, Any]]:
    """Convert each saved run folder into one normalized evaluation row."""
    runs = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        initial_path = folder / "initial_state.json"
        final_path = folder / "final_state.json"
        log_path = folder / "quantpilot.log"
        if not (initial_path.exists() or final_path.exists() or log_path.exists()):
            continue
        initial = read_json(initial_path)
        final = read_json(final_path) if final_path.exists() else None
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        runs.append(evaluate_run(initial, final, log_text, folder.name))
    return runs


def safe_rate(numerator: int, denominator: int) -> float | None:
    """Return a rounded rate, or None when the denominator is not meaningful."""
    return round(numerator / denominator, 4) if denominator else None


def build_summary(rows: list[dict]) -> dict:
    """Aggregate operational metrics while keeping interpretation limits explicit."""
    terminal = Counter(r["terminal_state"] for r in rows)
    input_guardrails = Counter(r["input_guardrail"] for r in rows)
    output_guardrails = Counter(r["output_guardrail_status"] for r in rows)
    decisions = Counter(r["adjudication_decision"] for r in rows)
    quality_bands = Counter(r["adjudication_quality_band"] for r in rows)
    evaluation_outcomes = Counter(r["evaluation_outcome"] for r in rows)
    final_reports = sum(bool(r["final_report_present"]) for r in rows)
    report_rows = [r for r in rows if r["final_report_present"]]
    completed_adjudications = sum(r["adjudication_decision"] in {"PASS", "FAIL"} for r in rows)
    quality_scores = [r["adjudication_quality_score"] for r in rows if isinstance(r["adjudication_quality_score"], (int, float))]
    plan_alignment = [r["query_plan_task_type_coverage"] for r in rows if isinstance(r["query_plan_task_type_coverage"], (int, float))]
    thesis_conf_valid_rows = [r for r in rows if r["thesis_present"]]
    critique_conf_valid_rows = [r for r in rows if r["critique_present"]]
    confidences = [r["final_report_confidence"] for r in rows if isinstance(r["final_report_confidence"], (int, float))]
    duration = [r["logged_node_duration_sum_seconds"] for r in rows if isinstance(r["logged_node_duration_sum_seconds"], (int, float))]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_count": len(rows),
        "terminal_states": dict(terminal),
        "input_guardrail_observations": dict(input_guardrails),
        "output_guardrail_observations": dict(output_guardrails),
        "adjudication_decisions": dict(decisions),
        "adjudication_quality_bands": dict(quality_bands),
        "evaluation_outcomes": dict(evaluation_outcomes),
        "final_report_completion_rate": safe_rate(final_reports, len(rows)),
        "final_report_schema_complete_rate": safe_rate(sum(r["final_report_schema_complete"] for r in report_rows), len(report_rows)),
        "final_report_thesis_consistency_rate": safe_rate(sum(r["final_report_thesis_consistent_with_generator"] for r in report_rows), len(report_rows)),
        "final_report_confidence_alignment_rate": safe_rate(sum(r["final_report_confidence_matches_adjudication"] for r in report_rows), len(report_rows)),
        "final_report_evidence_debt_disclosure_rate": safe_rate(sum(r["final_report_discloses_all_adjudication_debt"] for r in report_rows), len(report_rows)),
        "query_plan_task_type_alignment_rate": round(sum(plan_alignment) / len(plan_alignment), 4) if plan_alignment else None,
        "thesis_confidence_valid_range_rate": safe_rate(sum(r["thesis_confidence_valid_range"] for r in thesis_conf_valid_rows), len(thesis_conf_valid_rows)),
        "critique_confidence_valid_range_rate": safe_rate(sum(r["critique_confidence_valid_range"] for r in critique_conf_valid_rows), len(critique_conf_valid_rows)),
        "critique_flags_covered_by_adjudication_debt_rate": safe_rate(sum(r["critique_deterministic_flags_covered_by_adjudication_debt"] for r in rows if r["critique_present"] and r["adjudication_decision"] in {"PASS", "FAIL"}), sum(r["critique_present"] and r["adjudication_decision"] in {"PASS", "FAIL"} for r in rows)),
        "adjudication_decision_debt_consistency_rate": safe_rate(sum(r["adjudication_decision_consistent_with_debt"] for r in rows if r["adjudication_decision"] in {"PASS", "FAIL"}), sum(r["adjudication_decision"] in {"PASS", "FAIL"} for r in rows)),
        "adjudication_completion_rate": safe_rate(completed_adjudications, len(rows)),
        "adjudication_pass_rate_among_decided": safe_rate(decisions.get("PASS", 0), completed_adjudications),
        "mean_adjudication_quality_score": round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else None,
        "mean_final_report_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "mean_logged_node_duration_seconds": round(sum(duration) / len(duration), 3) if duration else None,
        "runs_with_replan": sum(r["replan_count"] > 0 for r in rows),
        "runs_with_log_error_signal": sum(r["run_failed_log_signal"] for r in rows),
        "runs_with_pii_redaction_signal": sum(r["pii_redaction_observed"] for r in rows),
        "metric_interpretation": {
            "completion_rates": "Artifact/log-derived operational rates; not answer correctness.",
            "adjudication_pass_rate": "System decision distribution; not independent adjudicator accuracy without labelled ground truth.",
            "evidence_duplicate_count": "Exact normalized duplicate tuples only; semantic duplicates require review.",
            "output_guardrail": "PASS_LOGGED reflects successful completion without logged issues; UNVERIFIED is kept distinct from PASS. Neither proves factual correctness.",
            "confidence": "Thesis and critique confidence are checked for presence/type/range only; semantic calibration requires independent labelled review and is not inferred from the model's own text.",
            "critique_adjudication": "Deterministic critique flags are checked against evidence debt and PASS/FAIL consistency; generated critique/rationale semantic quality is not independently scored.",
            "input_guardrail": "Input checks cover logged execution, scope acceptance/rejection, and PII redaction. They do not estimate false-positive/negative rates without labelled in-scope/out-of-scope queries.",
            "final_report": "Structural and cross-stage consistency checks; they do not establish factual correctness or claim-level faithfulness.",
            "query_plan_alignment": "Analyzer-to-plan consistency only; it does not establish that the analyzer correctly understood the user's intent.",
            "duration": "Sum of logged node durations; excludes unlogged setup and overhead.",
            "decision-->Fail": "Of the 11 adjudication-FAIL cases, 3 were rated STRONGLY_PASSED, 7 FAIRLY_PASSED, and 1 PARTIAL_PASS; none was FULLY_FAILED. PASS/FAIL is an evidence-sufficiency decision, not an independent factual-accuracy verdict.",
            "judge_quality_review": "Preliminary qualitative reviewer assessment of 18 saved runs (not deterministic code output, not an independent LLM-judge or human-adjudicated result): Evidence Builder mean confidence 0.909, with 206/206 structured market/financial/quantitative values matching saved tool results; status/content quality was mixed. Thesis Generator mean confidence 0.771 and content-quality assessment 3.22/5; Devil's Advocate mean confidence 0.675 and assessment 3.83/5 (strongest of the reviewed generators); Evidence Adjudicator mean confidence 0.768 and rationale assessment 3.39/5. Confidence-fit comments are also qualitative reviewer judgments, not statistical calibration; no Brier score, ECE, or reliability curve was computed.",
            "external_research_fidelity": "Preliminary heuristic review of 28 Tavily research-result records representing 21 distinct source-content items flagged possible prompt/meta-reasoning contamination in 10/28 records (8/21 distinct items); 2 summaries were under 500 characters and 6 were under half the corresponding source length. These length/contamination flags do not prove semantic omissions or factual corruption. The observed 512-token generation cap and reasoning/prompt overhead are plausible contributors, not a proven cause for every short summary. Passing suitable raw source.content to Evidence Builder is a possible mitigation, not an implemented feature.",
            "guardrail_reference_review": "Preliminary manual-reference assessment only. Input-scope review: 19 TP, 1 TN, 0 FP, 0 FN; input-length checks accepted 20 valid cases and rejected 1 below-minimum case. For output contextual review, 14 decided cases yielded 9 TP, 2 FP, 2 FN, and 1 TN (precision/recall 81.8%, FPR 66.7%, FNR 18.2%, specificity 33.3%); 4 UNVERIFIED cases were excluded, not counted as passes. Small manually reviewed samples are not benchmark-grade estimates.",
            "output_guardrail_review": "Across 21 runs, output-guardrail observations were 11 ISSUES_FOUND, 4 UNVERIFIED, 3 PASS_LOGGED, and 3 NOT_OBSERVED. UNVERIFIED means contextual review could not be completed reliably; it is neither a pass nor evidence of workflow failure. Structural report checks passed for 18/18 generated reports but do not establish factual correctness.",
            "evaluation_scope_caveats": "The 18 completed reports span two Final Report prompt versions (the first 12 and final 8 runs). Query-intent reference review found minimum required task-type coverage in 16/18 cases; the two misses were QP10 (SPY/QQQ historical-returns comparison) and QP14 (Microsoft market returns), both attributable to Query Analyzer omissions. These bounded results should not be generalized as overall analyzer accuracy.",
        }
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write a consistent UTF-8 CSV artifact for downstream inspection."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, summary: dict, rows: list[dict]) -> None:
    """Create the compact operational report; it is not a factual-accuracy scorecard."""
    lines = ["# QuantPilot Evaluation Snapshot", "", f"Generated: {summary['generated_at_utc']}", f"Runs discovered: **{summary['run_count']}**", "", "## Operational summary", "", "| Metric | Result |", "|---|---:|"]
    for label, key in [
        ("Final-report completion rate", "final_report_completion_rate"),
        ("Final-report schema completeness (among reports)", "final_report_schema_complete_rate"),
        ("Final-report thesis consistency (among reports)", "final_report_thesis_consistency_rate"),
        ("Final-report confidence alignment (among reports)", "final_report_confidence_alignment_rate"),
        ("Final-report evidence-debt disclosure (among reports)", "final_report_evidence_debt_disclosure_rate"),
        ("Analyzer-to-plan task-type alignment", "query_plan_task_type_alignment_rate"),
        ("Thesis confidence valid-range rate", "thesis_confidence_valid_range_rate"),
        ("Critique confidence valid-range rate", "critique_confidence_valid_range_rate"),
        ("Critique flags carried into adjudication debt", "critique_flags_covered_by_adjudication_debt_rate"),
        ("Adjudication decision/debt consistency", "adjudication_decision_debt_consistency_rate"),
        ("Adjudication completion rate", "adjudication_completion_rate"),
        ("PASS rate among decided cases", "adjudication_pass_rate_among_decided"),
        ("Mean adjudication quality score", "mean_adjudication_quality_score"),
        ("Mean final-report confidence", "mean_final_report_confidence"),
        ("Mean logged node duration (seconds)", "mean_logged_node_duration_seconds"),
        ("Runs with replan", "runs_with_replan"),
        ("Runs with error signal", "runs_with_log_error_signal"),
        ("Runs with PII-redaction signal", "runs_with_pii_redaction_signal"),
    ]:
        lines.append(f"| {label} | {summary.get(key)} |")
    lines += ["", "## Distributions", "", f"- Terminal states: `{summary['terminal_states']}`", f"- Input guardrail observations: `{summary['input_guardrail_observations']}`", f"- Output guardrail observations: `{summary['output_guardrail_observations']}`", f"- Adjudication decisions: `{summary['adjudication_decisions']}`", f"- Adjudication quality bands: `{summary['adjudication_quality_bands']}`", f"- Derived evaluation outcomes: `{summary['evaluation_outcomes']}`", "", "## Interpretation limits", ""]
    lines += [f"- {v}" for v in summary["metric_interpretation"].values()]
    lines += ["", "## Run-level exceptions / review queue", "", "| Run | Terminal | Decision | Quality band | Evaluation outcome | Output guardrail | Error signal |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["terminal_state"] != "FINAL_REPORT" or r["adjudication_decision"] != "PASS" or r["output_guardrail_status"] != "PASS_LOGGED" or r["run_failed_log_signal"]:
            lines.append(f"| {r['run_id']} | {r['terminal_state']} | {r['adjudication_decision']} | {r['adjudication_quality_band']} | {r['evaluation_outcome']} | {r['output_guardrail_status']} | {r['run_failed_log_signal']} |")

    lines += [
        "",
        "## Further Validation Scope",
        "",
        "The evaluation includes bounded manual query-intent assessment, preliminary confidence and generated-content quality reviews across all four judge nodes, and initial manual-reference guardrail FP/FN assessments.",
        "",
        "Future validation should focus on:",
        "- **Judge reliability:** Independent, stronger-LLM and human-assisted assessment of confidence calibration, evidence-status justification, thesis grounding, critique quality, and adjudication-rationale consistency.",
        "- **Guardrail reliability:** Larger labelled datasets for more robust FP/FN estimates.",
        "- **External research fidelity:** Deeper source-to-summary checks for factual coverage, omissions, unsupported additions, and potential raw Tavily-content fallback.",
        "",
        "These are planned extensions, not outstanding failures. Current deterministic and qualitative checks provide a useful baseline, not proof of factual correctness or statistically validated confidence calibration.",
        ""
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    # Expected project layout:
    # QuantPilot/
    #   QuantPilot_Samples/<run_id>/{initial_state.json, final_state.json, quantpilot.log}
    #   Evaluation/
    #     Eval_codefiles/{run_evaluation.py, metrics.py}
    #     Results/{evaluation_report.md, evaluation_summary.json, run_metrics.csv, ...}
    # Resolve defaults from this file's location so the evaluator can be run
    # from any working directory; CLI paths remain available for alternate datasets.
    evaluation_dir = Path(__file__).resolve().parents[1]
    project_root = evaluation_dir.parent
    default_runs_dir = project_root / "QuantPilot_Samples"
    default_output_dir = evaluation_dir / "Results"

    parser = argparse.ArgumentParser(
        description="Evaluate existing QuantPilot run folders without rerunning the workflow."
    )
    parser.add_argument(
        "--runs-dir", type=Path, default=default_runs_dir,
        help=f"Directory containing saved run folders (default: {default_runs_dir})"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=default_output_dir,
        help=f"Directory for evaluation outputs (default: {default_output_dir})"
    )
    args = parser.parse_args()

    if not args.runs_dir.is_dir():
        parser.error(f"Runs directory does not exist: {args.runs_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    # This is a post-run evaluator: it reads saved artifacts and never invokes the workflow.
    rows = load_runs(args.runs_dir)
    summary = build_summary(rows)
    # Keep machine-readable summary, per-run detail, and human-readable report in sync.
    (args.output_dir / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    write_csv(args.output_dir / "run_metrics.csv", rows)
    # Compact reference-label worksheet: only runs where the analyzer actually ran.
    # Preserve prior human labels by run_id so a later metrics refresh cannot erase the review.
    intent_path = args.output_dir / "query_intent_reference_review.csv"
    prior_intent = {}
    if intent_path.exists():
        with intent_path.open("r", newline="", encoding="utf-8-sig") as f:
            prior_intent = {item.get("run_id", ""): item for item in csv.DictReader(f)}
    intent_rows = []
    manual_fields = (
        "expected_task_types_reference", "intent_correctness_review", "review_notes",
        "missing_expected_task_types", "additional_unrequested_task_types", "reference_basis",
    )
    for r in rows:
        if r["query_analyzer_task_types"]:
            prior = prior_intent.get(r["run_id"], {})
            item = {
                "run_id": r["run_id"], "user_query": r["user_query"],
                "analyzer_task_types": r["query_analyzer_task_types"],
                "planned_task_types": r["planned_task_types"],
            }
            item.update({field: prior.get(field, "") for field in manual_fields})
            intent_rows.append(item)
    write_csv(intent_path, intent_rows)
    # Compact qualitative alignment worksheet. Preserve assessor-entered fields
    # by run_id so refreshing automatic metrics never erases manual review work.
    qualitative_path = args.output_dir / "qualitative_alignment_review.csv"
    prior_qualitative = {}
    if qualitative_path.exists():
        with qualitative_path.open("r", newline="", encoding="utf-8-sig") as f:
            prior_qualitative = {item.get("run_id", ""): item for item in csv.DictReader(f)}
    qualitative_manual_fields = (
        "thesis_confidence_justified_by_text",
        "critique_confidence_justified_by_critique",
        "critique_flags_match_text",
        "rationale_matches_critique_and_decision",
        "review_notes",
    )
    qualitative_rows = []
    for r in rows:
        if r["thesis_present"] or r["critique_present"] or r["adjudication_rationale_present"]:
            prior = prior_qualitative.get(r["run_id"], {})
            item = {
                "run_id": r["run_id"],
                "thesis": r.get("thesis_text_for_review", ""),
                "thesis_confidence": r.get("thesis_confidence"),
                "devils_advocate_critique": r.get("critique_text_for_review", ""),
                "critique_confidence": r.get("critique_confidence"),
                "adjudication_decision": r.get("adjudication_decision"),
                "adjudication_rationale": r.get("adjudication_rationale_for_review", ""),
            }
            item.update({field: prior.get(field, "") for field in qualitative_manual_fields})
            qualitative_rows.append(item)
    write_csv(qualitative_path, qualitative_rows)
    write_markdown(args.output_dir / "evaluation_report.md", summary, rows)
    print(f"Read runs from: {args.runs_dir.resolve()}")
    print(f"Evaluated {len(rows)} saved runs")
    print(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()