"""Controlled five-question smoke test after the generic prompt update."""

from __future__ import annotations

import json
from pathlib import Path

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.evidence_selector import EvidenceSelector
from cs_ingest.pipeline import QueryRetrievalPipeline

try:
    from .step10b_runner import (
        ROOT,
        SELECTOR_CONFIG,
        CapturingOllamaGenerator,
        _run_one,
    )
except ImportError:
    from evaluation.step10b_runner import (
        ROOT,
        SELECTOR_CONFIG,
        CapturingOllamaGenerator,
        _run_one,
    )


QUESTION_IDS = ("E001", "E006", "E014", "E016", "E017")


def run_smoke_test() -> dict:
    questions = json.loads(
        (ROOT / "evaluation" / "sample_questions.json").read_text(
            encoding="utf-8"
        )
    )
    question_by_id = {question["id"]: question for question in questions}
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
    for question_id in QUESTION_IDS:
        question = question_by_id[question_id]
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
                obligation_by_id[question_id],
            )
        )

    step10b = json.loads(
        (ROOT / "evaluation" / "step10b_live_evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    step10b_by_id = {
        result["id"]: result for result in step10b["results"]
    }
    comparison = {}
    for result in results:
        previous = step10b_by_id[result["id"]]
        comparison[result["id"]] = {
            "step10b_obligation": previous["obligation_evaluation"]["status"],
            "step11b_obligation": result["obligation_evaluation"]["status"],
            "step10b_conflict_complete": _complete(
                previous["obligation_evaluation"]["conflict_preservation"]
            ),
            "step11b_conflict_complete": _complete(
                result["obligation_evaluation"]["conflict_preservation"]
            ),
            "step10b_lifecycle_complete": _complete(
                previous["obligation_evaluation"]["lifecycle_distinction"]
            ),
            "step11b_lifecycle_complete": _complete(
                result["obligation_evaluation"]["lifecycle_distinction"]
            ),
            "step10b_latency_seconds": previous["latency_seconds"],
            "step11b_latency_seconds": result["latency_seconds"],
            "step10b_wrong_citation_obligations": previous[
                "obligation_evaluation"
            ]["wrong_citation_obligations"],
            "step11b_wrong_citation_obligations": result[
                "obligation_evaluation"
            ]["wrong_citation_obligations"],
        }

    return {
        "run_config": {
            "model": "gemma3:4b",
            "base_url": "http://localhost:11434",
            "timeout": 120.0,
            "selector": {
                "max_evidence_units": 3,
                "max_characters": 12000,
                "max_records": 8,
                "max_characters_per_unit": None,
            },
            "question_ids": list(QUESTION_IDS),
            "question_count": len(QUESTION_IDS),
            "attempts_per_question": 1,
            "retry_policy": "none",
        },
        "results": results,
        "comparison_with_step10b": comparison,
        "summary": _summary(results, comparison),
    }


def _complete(groups: list[dict]) -> bool | None:
    if not groups:
        return None
    return all(group["complete"] for group in groups)


def _summary(results: list[dict], comparison: dict) -> dict:
    statuses = [result["obligation_evaluation"]["status"] for result in results]
    return {
        "obligation_pass": statuses.count("PASS"),
        "obligation_partial": statuses.count("PARTIAL"),
        "obligation_fail": statuses.count("FAIL"),
        "model_api_failures": sum(
            result["model_api_failure"] is not None for result in results
        ),
        "conflict_complete_count": sum(
            item["step11b_conflict_complete"] is True
            for item in comparison.values()
        ),
        "lifecycle_complete_count": sum(
            item["step11b_lifecycle_complete"] is True
            for item in comparison.values()
        ),
        "average_latency_seconds": sum(
            result["latency_seconds"] for result in results
        )
        / len(results),
        "improved_obligation_cases": [
            question_id
            for question_id, item in comparison.items()
            if (
                item["step10b_obligation"] != "PASS"
                and item["step11b_obligation"] == "PASS"
            )
        ],
    }


def write_artifacts() -> None:
    artifact = run_smoke_test()
    (ROOT / "evaluation" / "step11b_smoke_test.json").write_text(
        json.dumps(artifact, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# STEP 11B Controlled Live Smoke Test",
        "",
        "## Configuration",
        "",
        "```json",
        json.dumps(artifact["run_config"], indent=2),
        "```",
        "",
        "## Per-question results",
        "",
        "| ID | Expected | Actual | Validator | Obligation | Missing obligations | Wrong citations | API failure |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for result in artifact["results"]:
        obligation = result["obligation_evaluation"]
        lines.append(
            f"| {result['id']} | {result['expected_status']} | "
            f"{result['actual_status']} | "
            f"{(result.get('validator') or {}).get('valid')} | "
            f"{obligation['status']} | {obligation['missing_obligations']} | "
            f"{obligation['wrong_citation_obligations']} | "
            f"{result['model_api_failure']} |"
        )
        lines.extend(
            [
                "",
                f"### {result['id']} details",
                "",
                f"- Selected evidence IDs: `{result['selected_evidence_ids']}`",
                f"- Claim-level output: `{json.dumps(result['claim_level_output'])}`",
                f"- Citation mapping: `{json.dumps(result['citation_handle_mapping'])}`",
                f"- Obligation evaluation: `{json.dumps(obligation)}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Step 10B vs Step 11B comparison",
            "",
            "| ID | Step 10B obligation | Step 11B obligation | Step 10B conflict | Step 11B conflict | Step 10B lifecycle | Step 11B lifecycle |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for question_id, item in artifact["comparison_with_step10b"].items():
        lines.append(
            f"| {question_id} | {item['step10b_obligation']} | "
            f"{item['step11b_obligation']} | {item['step10b_conflict_complete']} | "
            f"{item['step11b_conflict_complete']} | "
            f"{item['step10b_lifecycle_complete']} | "
            f"{item['step11b_lifecycle_complete']} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate comparison",
            "",
            f"- Step 11B summary: `{json.dumps(artifact['summary'])}`",
            "- Observable improvement is credited only where the deterministic obligation status improves or a required conflict/lifecycle group becomes complete.",
            "- No improvement is claimed from prompt wording, validator success, or citation-handle validity alone.",
            "",
            "## Citation correctness and latency",
            "",
        ]
    )
    for question_id, item in artifact["comparison_with_step10b"].items():
        lines.append(
            f"- {question_id}: wrong citations Step 10B "
            f"`{item['step10b_wrong_citation_obligations']}` -> Step 11B "
            f"`{item['step11b_wrong_citation_obligations']}`; latency "
            f"{item['step10b_latency_seconds']:.3f}s -> "
            f"{item['step11b_latency_seconds']:.3f}s."
        )
    (ROOT / "evaluation" / "STEP11B_SMOKE_TEST.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    write_artifacts()
