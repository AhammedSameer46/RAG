"""Controlled five-question smoke test for the integrated Answer Plan."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.citation_builder import citation_handles
from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.evidence_selector import EvidenceSelector
from cs_ingest.pipeline import QueryRetrievalPipeline

try:
    from .step10b_runner import (
        BASE_URL,
        MODEL,
        ROOT,
        SELECTOR_CONFIG,
        TIMEOUT,
        CapturingOllamaGenerator,
    )
    from .obligation_evaluator import evaluate_obligations
except ImportError:
    from evaluation.step10b_runner import (
        BASE_URL,
        MODEL,
        ROOT,
        SELECTOR_CONFIG,
        TIMEOUT,
        CapturingOllamaGenerator,
    )
    from evaluation.obligation_evaluator import evaluate_obligations


QUESTION_IDS = ("E001", "E006", "E014", "E016", "E017")


def run_smoke_test() -> dict[str, Any]:
    questions = _load_questions()
    obligations = _load_obligations()
    query_pipeline = QueryRetrievalPipeline.from_json(
        ROOT / "output" / "sample_normalized.json"
    )
    results = []
    for question_id in QUESTION_IDS:
        question = questions[question_id]
        capture = CapturingOllamaGenerator()
        pipeline = AnswerPipeline(
            query_pipeline,
            capture,
            EvidenceSelector(),
            SELECTOR_CONFIG,
        )
        results.append(
            _run_one(pipeline, capture, question, obligations[question_id])
        )
    return {
        "run_config": {
            "model": MODEL,
            "base_url": BASE_URL,
            "timeout": TIMEOUT,
            "selector": {
                "max_evidence_units": SELECTOR_CONFIG.max_evidence_units,
                "max_characters": SELECTOR_CONFIG.max_characters,
                "max_records": SELECTOR_CONFIG.max_records,
                "max_characters_per_unit": SELECTOR_CONFIG.max_characters_per_unit,
            },
            "question_ids": list(QUESTION_IDS),
            "question_count": len(QUESTION_IDS),
            "attempts_per_question": 1,
            "retry_policy": "none",
            "answer_plan_integrated": True,
            "evaluator": "evaluation.obligation_evaluator",
        },
        "results": results,
        "comparison": _comparison(results),
        "summary": _summary(results),
    }


def _run_one(
    pipeline: AnswerPipeline,
    capture: CapturingOllamaGenerator,
    question: dict[str, Any],
    obligation: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    result = None
    failure = None
    try:
        result = pipeline.run(question["question"])
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc)}
    latency = time.perf_counter() - started
    response = (result or {}).get("evidence_response", {})
    context = response.get("answer_context", {})
    selection = response.get("selection", {})
    handles = citation_handles(response) if context else {}
    selected = [
        evidence
        for collection in ("supporting_evidence", "independent_evidence")
        for evidence in context.get(collection, [])
    ]
    internal = capture.internal_output
    obligation_result: dict[str, Any] = {
        "status": "N/A",
        "reason": "not_applicable",
    }
    if failure is None and internal is not None and handles:
        obligation_result = evaluate_obligations(
            question["question"], obligation, internal, handles, selected
        )
    return {
        "id": question["id"],
        "question": question["question"],
        "expected_status": question["expected_status"],
        "actual_status": ((result or {}).get("answer") or {}).get("status"),
        "validator": (result or {}).get("validation"),
        "model_api_failure": failure,
        "latency_seconds": latency,
        "answer_plan": response.get("answer_plan"),
        "claim_level_output": internal,
        "citation_handle_mapping": {
            handle: value.get("evidence_id") for handle, value in handles.items()
        },
        "selected_evidence": selected,
        "selected_evidence_ids": selection.get("selected_evidence_ids", []),
        "selected_evidence_count": len(selected),
        "truncated": selection.get("truncated"),
        "selector_coverage": selection.get("coverage", {}),
        "obligation_evaluation": obligation_result,
        "final_answer_contract": (result or {}).get("answer"),
        "http_status": capture.http_status,
        "eval_count": capture.eval_count,
        "done_reason": capture.done_reason,
    }


def _load_questions() -> dict[str, dict[str, Any]]:
    data = json.loads(
        (ROOT / "evaluation" / "sample_questions.json").read_text(
            encoding="utf-8"
        )
    )
    return {item["id"]: item for item in data if item["id"] in QUESTION_IDS}


def _load_obligations() -> dict[str, dict[str, Any]]:
    data = json.loads(
        (ROOT / "evaluation" / "ANSWER_OBLIGATIONS.json").read_text(
            encoding="utf-8"
        )
    )["obligations"]
    return {item["id"]: item for item in data if item["id"] in QUESTION_IDS}


def _comparison(results: list[dict[str, Any]]) -> dict[str, Any]:
    previous = json.loads(
        (ROOT / "evaluation" / "step11b_smoke_test.json").read_text(
            encoding="utf-8"
        )
    )["results"]
    previous_by_id = {item["id"]: item for item in previous}
    comparison = {}
    for result in results:
        old = previous_by_id[result["id"]]
        old_eval = old["obligation_evaluation"]
        if result["id"] == "E014":
            baseline_status = "PARTIAL"
            baseline_label = "Step 11C corrected"
        else:
            baseline_status = old_eval["status"]
            baseline_label = "Step 11B"
        current = result["obligation_evaluation"]
        comparison[result["id"]] = {
            "baseline": baseline_label,
            "baseline_obligation": baseline_status,
            "answer_plan_obligation": current["status"],
            "baseline_conflict_complete": _complete(
                old_eval.get("conflict_preservation", [])
            ),
            "answer_plan_conflict_complete": _complete(
                current.get("conflict_preservation", [])
            ),
            "baseline_lifecycle_complete": _complete(
                old_eval.get("lifecycle_distinction", [])
            ),
            "answer_plan_lifecycle_complete": _complete(
                current.get("lifecycle_distinction", [])
            ),
            "baseline_wrong_citations": old_eval.get(
                "wrong_citation_obligations", []
            ),
            "answer_plan_wrong_citations": current.get(
                "wrong_citation_obligations", []
            ),
            "baseline_validator": (old.get("validator") or {}).get("valid"),
            "answer_plan_validator": (result.get("validator") or {}).get("valid"),
            "baseline_evidence_count": len(old.get("selected_evidence", [])),
            "answer_plan_evidence_count": result["selected_evidence_count"],
            "baseline_truncated": old.get("truncated"),
            "answer_plan_truncated": result["truncated"],
            "baseline_latency_seconds": old.get("latency_seconds"),
            "answer_plan_latency_seconds": result["latency_seconds"],
            "baseline_model_api_failure": old.get("model_api_failure"),
            "answer_plan_model_api_failure": result["model_api_failure"],
        }
    return comparison


def _complete(groups: list[dict[str, Any]]) -> bool | None:
    return None if not groups else all(group.get("complete") for group in groups)


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    evaluations = [item["obligation_evaluation"] for item in results]
    latencies = [item["latency_seconds"] for item in results]
    return {
        "total_questions": len(results),
        "expected_status_matches": sum(
            item["actual_status"] == "answered" for item in results
        ),
        "validator_passes": sum(
            bool((item.get("validator") or {}).get("valid")) for item in results
        ),
        "model_api_failures": sum(
            item["model_api_failure"] is not None for item in results
        ),
        "obligation_pass": sum(item["status"] == "PASS" for item in evaluations),
        "obligation_partial": sum(
            item["status"] == "PARTIAL" for item in evaluations
        ),
        "obligation_fail": sum(item["status"] == "FAIL" for item in evaluations),
        "average_latency_seconds": statistics.mean(latencies),
        "median_latency_seconds": statistics.median(latencies),
        "maximum_latency_seconds": max(latencies),
        "truncated_count": sum(item["truncated"] is True for item in results),
    }


def write_artifacts() -> None:
    existing = ROOT / "evaluation" / "step12d_answer_plan_smoke_test.json"
    if existing.exists():
        artifact = _enrich_persisted_failures(
            json.loads(existing.read_text(encoding="utf-8"))
        )
    else:
        artifact = run_smoke_test()
    json_path = ROOT / "evaluation" / "step12d_answer_plan_smoke_test.json"
    report_path = ROOT / "evaluation" / "STEP12D_ANSWER_PLAN_SMOKE_TEST.md"
    json_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# STEP 12D Answer Plan Smoke Test",
        "",
        "## Configuration",
        "",
        "```json",
        json.dumps(artifact["run_config"], indent=2),
        "```",
        "",
        "## Per-question results",
        "",
        "| ID | Expected | Actual | Validator | Evidence | Truncated | Obligation | Missing | Wrong citations | API failure |",
        "|---|---|---|---|---:|---|---|---|---|---|",
    ]
    for result in artifact["results"]:
        evaluation = result["obligation_evaluation"]
        lines.append(
            f"| {result['id']} | {result['expected_status']} | "
            f"{result['actual_status']} | {(result.get('validator') or {}).get('valid')} | "
            f"{result['selected_evidence_count']} | {result['truncated']} | "
            f"{evaluation['status']} | {evaluation.get('missing_obligations', [])} | "
            f"{evaluation.get('wrong_citation_obligations', [])} | "
            f"{result['model_api_failure']} |"
        )
        lines.extend(
            [
                "",
                f"### {result['id']} details",
                "",
                f"- Answer Plan: `{json.dumps(result['answer_plan'], sort_keys=True)}`",
                f"- Selected evidence IDs: `{result['selected_evidence_ids']}`",
                f"- Claim-level output: `{json.dumps(result['claim_level_output'])}`",
                f"- Citation mapping: `{json.dumps(result['citation_handle_mapping'])}`",
                f"- Obligation evaluation: `{json.dumps(evaluation)}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Baseline comparison",
            "",
            "E014 uses the corrected Step 11C classification as its baseline; all other cases use Step 11B.",
            "",
            "| ID | Baseline | Plan obligation | Baseline conflict | Plan conflict | Baseline lifecycle | Plan lifecycle | Baseline citations | Plan citations | Baseline validator | Plan validator | Baseline evidence | Plan evidence | Baseline latency | Plan latency |",
            "|---|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for question_id, item in artifact["comparison"].items():
        lines.append(
            f"| {question_id} | {item['baseline_obligation']} ({item['baseline']}) | "
            f"{item['answer_plan_obligation']} | {item['baseline_conflict_complete']} | "
            f"{item['answer_plan_conflict_complete']} | {item['baseline_lifecycle_complete']} | "
            f"{item['answer_plan_lifecycle_complete']} | {item['baseline_wrong_citations']} | "
            f"{item['answer_plan_wrong_citations']} | {item['baseline_validator']} | "
            f"{item['answer_plan_validator']} | {item['baseline_evidence_count']} | "
            f"{item['answer_plan_evidence_count']} | {item['baseline_latency_seconds']:.3f} | "
            f"{item['answer_plan_latency_seconds']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate result",
            "",
            f"```json\n{json.dumps(artifact['summary'], indent=2)}\n```",
            "",
            "Improvement is credited only when deterministic obligation outcomes improve without citation or validator regressions.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _enrich_persisted_failures(artifact: dict[str, Any]) -> dict[str, Any]:
    """Add deterministic pre-generation data without rerunning provider calls."""
    questions = _load_questions()
    query_pipeline = QueryRetrievalPipeline.from_json(
        ROOT / "output" / "sample_normalized.json"
    )
    selector = EvidenceSelector()
    for result in artifact["results"]:
        if result.get("answer_plan") is not None:
            continue
        question = questions[result["id"]]
        evidence_response = build_evidence_response(
            query_pipeline.run(question["question"])
        )
        selection = selector.select(
            question["question"],
            evidence_response["query_understanding"],
            evidence_response,
            SELECTOR_CONFIG,
        )
        selected_response = dict(evidence_response)
        selected_response["answer_context"] = {
            "records": selection["selected_records"],
            "supporting_evidence": selection["selected_supporting_evidence"],
            "independent_evidence": selection["selected_independent_evidence"],
        }
        selected_response["selection"] = selection["selection_metadata"]
        selected_response["coverage"] = selection["selection_metadata"]["coverage"]
        result["answer_plan"] = build_answer_plan(selected_response)
        result["selected_evidence"] = [
            evidence
            for collection in (
                selection["selected_supporting_evidence"],
                selection["selected_independent_evidence"],
            )
            for evidence in collection
        ]
        result["selected_evidence_ids"] = sorted(
            evidence["evidence_id"] for evidence in result["selected_evidence"]
        )
        result["selected_evidence_count"] = len(result["selected_evidence"])
        result["truncated"] = selection["selection_metadata"]["truncated"]
        result["selector_coverage"] = selection["selection_metadata"]["coverage"]
        result["citation_handle_mapping"] = {
            handle: evidence["evidence_id"]
            for handle, evidence in citation_handles(selected_response).items()
        }
    artifact["summary"] = _summary(artifact["results"])
    artifact["comparison"] = _comparison(artifact["results"])
    return artifact


if __name__ == "__main__":
    write_artifacts()
