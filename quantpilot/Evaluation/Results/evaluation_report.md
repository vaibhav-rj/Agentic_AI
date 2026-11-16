# QuantPilot Evaluation Snapshot

Generated: 2026-11-15T23:36:13.600723+00:00
Runs discovered: **21**

## Operational summary

| Metric | Result |
|---|---:|
| Final-report completion rate | 0.8571 |
| Final-report schema completeness (among reports) | 1.0 |
| Final-report thesis consistency (among reports) | 1.0 |
| Final-report confidence alignment (among reports) | 1.0 |
| Final-report evidence-debt disclosure (among reports) | 1.0 |
| Analyzer-to-plan task-type alignment | 1.0 |
| Thesis confidence valid-range rate | 1.0 |
| Critique confidence valid-range rate | 1.0 |
| Critique flags carried into adjudication debt | 1.0 |
| Adjudication decision/debt consistency | 1.0 |
| Adjudication completion rate | 0.8571 |
| PASS rate among decided cases | 0.3889 |
| Mean adjudication quality score | 0.8255 |
| Mean final-report confidence | 0.7678 |
| Mean logged node duration (seconds) | 167.641 |
| Runs with replan | 18 |
| Runs with error signal | 3 |
| Runs with PII-redaction signal | 5 |

## Distributions

- Terminal states: `{'FINAL_REPORT': 18, 'GUARDRAIL_REJECTED': 2, 'INCOMPLETE_OR_FAILED': 1}`
- Input guardrail observations: `{'ACCEPTED': 19, 'REJECTED': 2}`
- Output guardrail observations: `{'ISSUES_FOUND': 11, 'UNVERIFIED': 4, 'NOT_OBSERVED': 3, 'PASS_LOGGED': 3}`
- Adjudication decisions: `{'FAIL': 11, 'PASS': 7, 'NOT_REACHED': 3}`
- Adjudication quality bands: `{'FAIRLY_PASSED': 7, 'FULLY_PASSED': 7, 'STRONGLY_PASSED': 3, 'NOT_RECORDED': 3, 'AVERAGE': 1}`
- Derived evaluation outcomes: `{'FAIRLY_PASSED': 7, 'FULLY_PASSED': 7, 'STRONGLY_PASSED': 3, 'REVIEW_REQUIRED': 3, 'PARTIAL_PASS': 1}`

## Interpretation limits

- Artifact/log-derived operational rates; not answer correctness.
- System decision distribution; not independent adjudicator accuracy without labelled ground truth.
- Exact normalized duplicate tuples only; semantic duplicates require review.
- PASS_LOGGED reflects successful completion without logged issues; UNVERIFIED is kept distinct from PASS. Neither proves factual correctness.
- Thesis and critique confidence are checked for presence/type/range only; semantic calibration requires independent labelled review and is not inferred from the model's own text.
- Deterministic critique flags are checked against evidence debt and PASS/FAIL consistency; generated critique/rationale semantic quality is not independently scored.
- Input checks cover logged execution, scope acceptance/rejection, and PII redaction. They do not estimate false-positive/negative rates without labelled in-scope/out-of-scope queries.
- Structural and cross-stage consistency checks; they do not establish factual correctness or claim-level faithfulness.
- Analyzer-to-plan consistency only; it does not establish that the analyzer correctly understood the user's intent.
- Sum of logged node durations; excludes unlogged setup and overhead.
- Of the 11 adjudication-FAIL cases, 3 were rated STRONGLY_PASSED, 7 FAIRLY_PASSED, and 1 PARTIAL_PASS; none was FULLY_FAILED. PASS/FAIL is an evidence-sufficiency decision, not an independent factual-accuracy verdict.
- Preliminary qualitative reviewer assessment of 18 saved runs (not deterministic code output, not an independent LLM-judge or human-adjudicated result): Evidence Builder mean confidence 0.909, with 206/206 structured market/financial/quantitative values matching saved tool results; status/content quality was mixed. Thesis Generator mean confidence 0.771 and content-quality assessment 3.22/5; Devil's Advocate mean confidence 0.675 and assessment 3.83/5 (strongest of the reviewed generators); Evidence Adjudicator mean confidence 0.768 and rationale assessment 3.39/5. Confidence-fit comments are also qualitative reviewer judgments, not statistical calibration; no Brier score, ECE, or reliability curve was computed.
- Preliminary heuristic review of 28 Tavily research-result records representing 21 distinct source-content items flagged possible prompt/meta-reasoning contamination in 10/28 records (8/21 distinct items); 2 summaries were under 500 characters and 6 were under half the corresponding source length. These length/contamination flags do not prove semantic omissions or factual corruption. The observed 512-token generation cap and reasoning/prompt overhead are plausible contributors, not a proven cause for every short summary. Passing suitable raw source.content to Evidence Builder is a possible mitigation, not an implemented feature.
- Preliminary manual-reference assessment only. Input-scope review: 19 TP, 1 TN, 0 FP, 0 FN; input-length checks accepted 20 valid cases and rejected 1 below-minimum case. For output contextual review, 14 decided cases yielded 9 TP, 2 FP, 2 FN, and 1 TN (precision/recall 81.8%, FPR 66.7%, FNR 18.2%, specificity 33.3%); 4 UNVERIFIED cases were excluded, not counted as passes. Small manually reviewed samples are not benchmark-grade estimates.
- Across 21 runs, output-guardrail observations were 11 ISSUES_FOUND, 4 UNVERIFIED, 3 PASS_LOGGED, and 3 NOT_OBSERVED. UNVERIFIED means contextual review could not be completed reliably; it is neither a pass nor evidence of workflow failure. Structural report checks passed for 18/18 generated reports but do not establish factual correctness.
- The 18 completed reports span two Final Report prompt versions (the first 12 and final 8 runs). Query-intent reference review found minimum required task-type coverage in 16/18 cases; the two misses were QP10 (SPY/QQQ historical-returns comparison) and QP14 (Microsoft market returns), both attributable to Query Analyzer omissions. These bounded results should not be generalized as overall analyzer accuracy.

## Run-level exceptions / review queue

| Run | Terminal | Decision | Quality band | Evaluation outcome | Output guardrail | Error signal |
|---|---|---|---|---|---|---|
| 20261113_153553 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | ISSUES_FOUND | False |
| 20261113_192304 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | ISSUES_FOUND | False |
| 20261113_194259 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | UNVERIFIED | False |
| 20261113_195420 | FINAL_REPORT | PASS | FULLY_PASSED | FULLY_PASSED | UNVERIFIED | False |
| 20261113_202108 | FINAL_REPORT | FAIL | STRONGLY_PASSED | STRONGLY_PASSED | ISSUES_FOUND | False |
| 20261113_203549 | FINAL_REPORT | PASS | FULLY_PASSED | FULLY_PASSED | ISSUES_FOUND | False |
| 20261113_205401 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | ISSUES_FOUND | False |
| 20261113_210839 | FINAL_REPORT | PASS | FULLY_PASSED | FULLY_PASSED | UNVERIFIED | False |
| 20261113_211915 | GUARDRAIL_REJECTED | NOT_REACHED | NOT_RECORDED | REVIEW_REQUIRED | NOT_OBSERVED | True |
| 20261113_212342 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | ISSUES_FOUND | False |
| 20261113_215045 | FINAL_REPORT | FAIL | STRONGLY_PASSED | STRONGLY_PASSED | ISSUES_FOUND | False |
| 20261114_012733 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | UNVERIFIED | False |
| 20261114_015943 | FINAL_REPORT | PASS | FULLY_PASSED | FULLY_PASSED | ISSUES_FOUND | False |
| 20261115_141438 | FINAL_REPORT | PASS | FULLY_PASSED | FULLY_PASSED | ISSUES_FOUND | False |
| 20261115_142810 | FINAL_REPORT | FAIL | AVERAGE | PARTIAL_PASS | ISSUES_FOUND | False |
| 20261115_144239 | INCOMPLETE_OR_FAILED | NOT_REACHED | NOT_RECORDED | REVIEW_REQUIRED | NOT_OBSERVED | True |
| 20261115_145232 | FINAL_REPORT | FAIL | STRONGLY_PASSED | STRONGLY_PASSED | PASS_LOGGED | False |
| 20261115_153218 | FINAL_REPORT | PASS | FULLY_PASSED | FULLY_PASSED | ISSUES_FOUND | False |
| 20261115_155641 | FINAL_REPORT | FAIL | FAIRLY_PASSED | FAIRLY_PASSED | PASS_LOGGED | False |
| 20261115_160839 | GUARDRAIL_REJECTED | NOT_REACHED | NOT_RECORDED | REVIEW_REQUIRED | NOT_OBSERVED | True |

## Further Validation Scope

The evaluation includes bounded manual query-intent assessment, preliminary confidence and generated-content quality reviews across all four judge nodes, and initial manual-reference guardrail FP/FN assessments.

Future validation should focus on:
- **Judge reliability:** Independent, stronger-LLM and human-assisted assessment of confidence calibration, evidence-status justification, thesis grounding, critique quality, and adjudication-rationale consistency.
- **Guardrail reliability:** Larger labelled datasets for more robust FP/FN estimates.
- **External research fidelity:** Deeper source-to-summary checks for factual coverage, omissions, unsupported additions, and potential raw Tavily-content fallback.

These are planned extensions, not outstanding failures. Current deterministic and qualitative checks provide a useful baseline, not proof of factual correctness or statistically validated confidence calibration.
