"""Step 10B evaluation runner and deterministic obligation integration."""

from __future__ import annotations

import json
import statistics
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
from urllib import request

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.citation_builder import citation_handles
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.ollama_answer_generator import OllamaAnswerGenerator
from cs_ingest.pipeline import QueryRetrievalPipeline

from .obligation_evaluator import evaluate_obligations


ROOT = Path(__file__).parents[1]
MODEL = "gemma3:4b"
BASE_URL = "http://localhost:11434"
TIMEOUT = 120.0
SELECTOR_CONFIG = EvidenceSelectionConfig(
    max_evidence_units=3,
    max_characters=12000,
    max_records=8,
    max_characters_per_unit=None,
)


class CapturingOllamaGenerator:
    """Capture provider telemetry without changing provider behavior."""

    def __init__(self) -> None:
        self.provider = OllamaAnswerGenerator(
            base_url=BASE_URL, model=MODEL, timeout=TIMEOUT
        )
        self.internal_output: dict[str, Any] | None = None
        self.request_payload: dict[str, Any] | None = None
        self.raw_response: str | None = None
        self.http_status: int | None = None
        self.eval_count: int | None = None
        self.done_reason: str | None = None

    def generate(
        self, question: str, evidence_response: dict[str, Any]
    ) -> dict[str, Any]:
        original_urlopen = request.urlopen

        def capture(http_request, timeout=None):
            self.request_payload = json.loads(
                http_request.data.decode("utf-8")
            )
            response = original_urlopen(http_request, timeout=timeout)
            self.http_status = getattr(response, "status", None)
            raw = response.read()
            self.raw_response = raw.decode("utf-8", errors="replace")
            envelope = json.loads(self.raw_response)
            self.eval_count = envelope.get("eval_count")
            self.done_reason = envelope.get("done_reason")

            class ReplayResponse:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return raw

            return ReplayResponse()

        request.urlopen = capture
        try:
            self.internal_output = self.provider.generate(
                question, evidence_response
            )
            return self.internal_output
        finally:
            request.urlopen = original_urlopen


def run_live_evaluation() -> dict[str, Any]:
    """Run the fixed 17-question evaluation exactly once per question."""
    questions = json.loads(
        (ROOT / "evaluation" / "sample_questions.json").read_text(
            encoding="utf-8"
        )
    )
    obligations = json.loads(
        (ROOT / "evaluation" / "ANSWER_OBLIGATIONS.json").read_text(
            encoding="utf-8"
        )
    )["obligations"]
    obligation_by_id = {item["id"]: item for item in obligations}
    query_pipeline = QueryRetrievalPipeline.from_json(
        ROOT / "output" / "sample_normalized.json"
    )
    results = []
    for question in questions:
        capture = CapturingOllamaGenerator()
        pipeline = AnswerPipeline(
            query_pipeline,
            capture,
            EvidenceSelector(),
            SELECTOR_CONFIG,
        )
        results.append(
            _run_one(
                pipeline,
                capture,
                question,
                obligation_by_id.get(question["id"]),
            )
        )
    return _build_artifact(results)


def _run_one(
    pipeline: AnswerPipeline,
    capture: CapturingOllamaGenerator,
    question: dict[str, Any],
    obligation: dict[str, Any] | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    result = None
    exception = None
    try:
        result = pipeline.run(question["question"])
    except Exception as exc:
        exception = {"type": type(exc).__name__, "message": str(exc)}
    latency = time.perf_counter() - started
    evidence_response = (result or {}).get("evidence_response", {})
    selection = evidence_response.get("selection", {})
    final_answer = (result or {}).get("answer")
    handles = (
        citation_handles(evidence_response)
        if evidence_response.get("answer_context")
        else {}
    )
    selected = [
        evidence
        for collection in ("supporting_evidence", "independent_evidence")
        for evidence in evidence_response.get("answer_context", {}).get(
            collection, []
        )
    ]
    internal = capture.internal_output
    obligation_result = {"status": "N/A", "reason": "not_applicable"}
    if (
        obligation is not None
        and exception is None
        and internal is not None
        and handles
    ):
        obligation_result = evaluate_obligations(
            question["question"], obligation, internal, handles, selected
        )
    return {
        "id": question["id"],
        "question": question["question"],
        "expected_status": question["expected_status"],
        "actual_status": (
            final_answer.get("status")
            if isinstance(final_answer, dict)
            else None
        ),
        "validator": (result or {}).get("validation"),
        "model_api_failure": exception,
        "latency_seconds": latency,
        "claim_level_output": internal,
        "citation_handle_mapping": {
            handle: value.get("evidence_id")
            for handle, value in handles.items()
        },
        "selected_evidence": selected,
        "selected_evidence_ids": selection.get("selected_evidence_ids", []),
        "excluded_evidence_ids": selection.get(
            "excluded_evidence_ids", []
        ),
        "selector_coverage": selection.get("coverage", {}),
        "truncated": selection.get("truncated"),
        "final_answer_contract": final_answer,
        "obligation_evaluation": obligation_result,
        "http_status": capture.http_status,
        "eval_count": capture.eval_count,
        "done_reason": capture.done_reason,
    }


def _build_artifact(results: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [
        result for result in results if result["expected_status"] == "answerable"
    ]
    statuses_match = sum(
        (
            result["actual_status"] == "answered"
            if result["expected_status"] == "answerable"
            else result["actual_status"] == result["expected_status"]
        )
        for result in results
    )
    validator_passes = sum(
        bool((result.get("validator") or {}).get("valid"))
        for result in results
    )
    obligations = [result["obligation_evaluation"] for result in results]
    latencies = [result["latency_seconds"] for result in results]
    summary = {
        "total_questions": len(results),
        "expected_status_matches": statuses_match,
        "validator_passes": validator_passes,
        "valid_citation_handles": sum(
            bool(result["citation_handle_mapping"])
            and not result["obligation_evaluation"].get(
                "invalid_evidence_handles"
            )
            for result in answerable
        ),
        "model_api_failures": sum(
            result["model_api_failure"] is not None for result in results
        ),
        "obligation_pass": sum(
            item["status"] == "PASS" for item in obligations
        ),
        "obligation_partial": sum(
            item["status"] == "PARTIAL" for item in obligations
        ),
        "obligation_fail": sum(
            item["status"] == "FAIL" for item in obligations
        ),
        "obligation_na": sum(item["status"] == "N/A" for item in obligations),
        "wrong_citation_obligations": sum(
            bool(item.get("wrong_citation_obligations"))
            for item in obligations
        ),
        "conflict_preservation": sum(
            all(group["complete"] for group in item["conflict_preservation"])
            for item in obligations
            if item["status"] != "N/A"
        ),
        "lifecycle_distinction": sum(
            all(group["complete"] for group in item["lifecycle_distinction"])
            for item in obligations
            if item["status"] != "N/A"
        ),
        "incomplete_answerable": sum(
            item["status"] in {"PARTIAL", "FAIL"}
            for item in obligations
            if item["status"] != "N/A"
        ),
        "average_latency_seconds": statistics.mean(latencies) if latencies else 0,
        "median_latency_seconds": statistics.median(latencies) if latencies else 0,
        "maximum_latency_seconds": max(latencies) if latencies else 0,
        "truncated_selections": sum(
            bool(result["truncated"]) for result in results
        ),
    }
    return {
        "run_config": {
            "model": MODEL,
            "base_url": BASE_URL,
            "timeout": TIMEOUT,
            "selector": {
                "max_evidence_units": 3,
                "max_characters": 12000,
                "max_records": 8,
                "max_characters_per_unit": None,
            },
            "question_count": 17,
            "attempts_per_question": 1,
            "retry_policy": "none",
        },
        "summary": summary,
        "results": deepcopy(results),
    }


def write_report(artifact: dict[str, Any]) -> None:
    output = ROOT / "evaluation" / "step10b_live_evaluation.json"
    output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    lines = [
        "# STEP 10B Live Evaluation",
        "",
        "## Run configuration",
        "",
        "```json",
        json.dumps(artifact["run_config"], indent=2),
        "```",
        "",
        "## Aggregate results",
        "",
        "| Metric | Result |",
        "|---|---:|",
    ]
    for key, value in artifact["summary"].items():
        lines.append(f"| {key} | {value} |")
    step9_path = ROOT / "evaluation" / "step9_live_evaluation.json"
    if step9_path.exists():
        step9 = json.loads(step9_path.read_text(encoding="utf-8"))
        lines.extend(
            [
                "",
                "## Comparison with STEP 9",
                "",
                "| Metric | STEP 9 | STEP 10B |",
                "|---|---:|---:|",
            ]
        )
        for key in (
            "expected_status_matches",
            "validator_passes",
            "valid_citation_handles",
            "model_api_failures",
            "incomplete_answerable",
            "average_latency_seconds",
            "median_latency_seconds",
            "maximum_latency_seconds",
            "truncated_selections",
        ):
            lines.append(
                f"| {key} | {step9.get('summary', {}).get(key, 'not recorded')} | "
                f"{artifact['summary'].get(key)} |"
            )
    lines.extend(
        [
            "",
            "## Per-question results",
            "",
            "| ID | Expected Status | Actual Status | Validator | Obligation | Key Failure |",
            "|---|---|---|---|---|---|",
        ]
    )
    for result in artifact["results"]:
        obligation = result["obligation_evaluation"]
        failure = (
            obligation.get("missing_obligations")
            or obligation.get("wrong_citation_obligations")
            or result["model_api_failure"]
            or ""
        )
        lines.append(
            f"| {result['id']} | {result['expected_status']} | "
            f"{result['actual_status']} | "
            f"{(result.get('validator') or {}).get('valid')} | "
            f"{obligation['status']} | {failure} |"
        )
    lines.extend(["", "## Focused analysis", ""])
    for case_id in ("E001", "E006", "E014", "E016", "E017"):
        result = next(item for item in artifact["results"] if item["id"] == case_id)
        lines.extend(
            [
                f"### {case_id}",
                "",
                f"- Selected evidence IDs: `{result['selected_evidence_ids']}`",
                f"- Selector coverage: `{json.dumps(result['selector_coverage'])}`",
                f"- Claim output: `{json.dumps(result['claim_level_output'])}`",
                f"- Obligation result: `{json.dumps(result['obligation_evaluation'])}`",
                "",
            ]
        )
    (ROOT / "evaluation" / "STEP10B_LIVE_EVALUATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    write_report(run_live_evaluation())
