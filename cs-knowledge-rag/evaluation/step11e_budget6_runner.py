"""Step 11E evaluation-only evidence-budget experiment."""

from __future__ import annotations

import json
from pathlib import Path

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.pipeline import QueryRetrievalPipeline

from .step10b_runner import ROOT, CapturingOllamaGenerator, _run_one


QUESTION_IDS = ("E006", "E014", "E016", "E017")
EXPERIMENT_CONFIG = EvidenceSelectionConfig(
    max_evidence_units=6,
    max_characters=12000,
    max_records=8,
    max_characters_per_unit=None,
)


def run_experiment() -> dict:
    questions = json.loads(
        (ROOT / "evaluation" / "sample_questions.json").read_text(
            encoding="utf-8"
        )
    )
    question_by_id = {item["id"]: item for item in questions}
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
            EXPERIMENT_CONFIG,
        )
        result = _run_one(
            pipeline,
            capture,
            question,
            obligation_by_id[question_id],
        )
        result["selected_evidence_count"] = len(result["selected_evidence"])
        result["conflict_preservation"] = result["obligation_evaluation"][
            "conflict_preservation"
        ]
        result["lifecycle_preservation"] = result["obligation_evaluation"][
            "lifecycle_distinction"
        ]
        results.append(result)

    previous = json.loads(
        (ROOT / "evaluation" / "step11b_smoke_test.json").read_text(
            encoding="utf-8"
        )
    )
    previous_by_id = {item["id"]: item for item in previous["results"]}
    comparison = {}
    for result in results:
        old = previous_by_id[result["id"]]
        comparison[result["id"]] = {
            "step11b": _comparison_fields(old),
            "step11e": _comparison_fields(result),
        }

    not_recorded_e001 = {
        "id": "E001",
        "execution_status": "not_recorded",
        "reason": (
            "The single allowed Step 11E Ollama attempt completed, but the "
            "evaluation harness failed before persisting the result. E001 "
            "was not rerun."
        ),
    }
    return {
        "run_config": {
            "model": "gemma3:4b",
            "base_url": "http://localhost:11434",
            "timeout": 120.0,
            "selector": {
                "max_evidence_units": 6,
                "max_characters": 12000,
                "max_records": 8,
                "max_characters_per_unit": None,
            },
            "question_ids": ["E001", *QUESTION_IDS],
            "executed_question_ids": list(QUESTION_IDS),
            "not_recorded_question_ids": ["E001"],
            "question_count": 5,
            "attempts_per_question": 1,
            "retry_policy": "none",
        },
        "results": [not_recorded_e001, *results],
        "comparison_with_step11b": comparison,
        "summary": _summary([not_recorded_e001, *results]),
    }


def _comparison_fields(result: dict) -> dict:
    obligation = result["obligation_evaluation"]
    return {
        "selected_evidence_count": len(result["selected_evidence"]),
        "truncated": result["truncated"],
        "obligation_status": obligation["status"],
        "conflict_complete": _complete(obligation["conflict_preservation"]),
        "lifecycle_complete": _complete(obligation["lifecycle_distinction"]),
        "wrong_citation_obligations": obligation[
            "wrong_citation_obligations"
        ],
        "validator": (result.get("validator") or {}).get("valid"),
        "latency_seconds": result["latency_seconds"],
    }


def _complete(groups: list[dict]) -> bool | None:
    if not groups:
        return None
    return all(group["complete"] for group in groups)


def _summary(results: list[dict]) -> dict:
    executed = [item for item in results if "obligation_evaluation" in item]
    statuses = [item["obligation_evaluation"]["status"] for item in executed]
    return {
        "executed_question_count": len(executed),
        "not_recorded_question_ids": [
            item["id"] for item in results if item.get("execution_status") == "not_recorded"
        ],
        "obligation_pass": statuses.count("PASS"),
        "obligation_partial": statuses.count("PARTIAL"),
        "obligation_fail": statuses.count("FAIL"),
        "model_api_failures": sum(
            item["model_api_failure"] is not None for item in executed
        ),
        "truncated_count": sum(bool(item["truncated"]) for item in executed),
        "average_latency_seconds": sum(
            item["latency_seconds"] for item in executed
        )
        / len(executed),
    }


def write_artifacts() -> None:
    artifact = run_experiment()
    (ROOT / "evaluation" / "step11e_budget6_smoke_test.json").write_text(
        json.dumps(artifact, indent=2) + "\n",
        encoding="utf-8",
    )
    write_report(artifact)


def write_report(artifact: dict) -> None:
    lines = [
        "# STEP 11E Evidence-Budget Experiment",
        "",
        "## Configuration",
        "",
        "This is an evaluation-only run using the Step 11A prompt and the "
        "Step 11B configuration, with only `max_evidence_units` changed "
        "from 3 to 6.",
        "",
        "```json",
        json.dumps(artifact["run_config"], indent=2),
        "```",
        "",
        "## Per-question results",
        "",
        "| ID | Expected | Actual | Selected units | Truncated | Validator | Obligation | Missing obligations | Wrong citations | Latency |",
        "|---|---|---|---:|---|---|---|---|---|---:|",
    ]
    for result in artifact["results"]:
        if result.get("execution_status") == "not_recorded":
            lines.append(
                f"| {result['id']} | not recorded | not recorded | — | — | — | — | — | — | — |"
            )
            continue
        obligation = result["obligation_evaluation"]
        lines.append(
            f"| {result['id']} | {result['expected_status']} | "
            f"{result['actual_status']} | {result['selected_evidence_count']} | "
            f"{result['truncated']} | "
            f"{(result.get('validator') or {}).get('valid')} | "
            f"{obligation['status']} | {obligation['missing_obligations']} | "
            f"{obligation['wrong_citation_obligations']} | "
            f"{result['latency_seconds']:.3f}s |"
        )
    lines.extend(
        [
            "",
            "## Step 11B versus Step 11E",
            "",
            "E001 has no valid Step 11B-versus-Step 11E comparison because its single Step 11E attempt was not persisted and was not rerun.",
            "",
            "| ID | 11B units | 11E units | 11B truncation | 11E truncation | 11B obligation | 11E obligation | 11B conflict | 11E conflict | 11B lifecycle | 11E lifecycle | 11B citation errors | 11E citation errors | 11B validator | 11E validator | 11B latency | 11E latency |",
            "|---|---:|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---:|",
        ]
    )
    for question_id, comparison in artifact["comparison_with_step11b"].items():
        old = comparison["step11b"]
        new = comparison["step11e"]
        lines.append(
            f"| {question_id} | {old['selected_evidence_count']} | "
            f"{new['selected_evidence_count']} | {old['truncated']} | "
            f"{new['truncated']} | {old['obligation_status']} | "
            f"{new['obligation_status']} | {old['conflict_complete']} | "
            f"{new['conflict_complete']} | {old['lifecycle_complete']} | "
            f"{new['lifecycle_complete']} | "
            f"{old['wrong_citation_obligations']} | "
            f"{new['wrong_citation_obligations']} | {old['validator']} | "
            f"{new['validator']} | {old['latency_seconds']:.3f}s | "
            f"{new['latency_seconds']:.3f}s |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Aggregate Step 11E summary: `{json.dumps(artifact['summary'])}`",
            "- More selected evidence is not treated as improvement by itself.",
            "- The experiment succeeds only where deterministic obligation outcomes improve without citation or grounding regressions.",
            "- Model outputs were generated once per question and are preserved in the JSON artifact.",
        ]
    )
    for result in artifact["results"]:
        if result.get("execution_status") == "not_recorded":
            continue
        lines.extend(
            [
                "",
                f"### {result['id']} evidence and obligation details",
                "",
                f"- Selected evidence IDs: `{result['selected_evidence_ids']}`",
                f"- Selector coverage: `{json.dumps(result['selector_coverage'])}`",
                f"- Claim-level output: `{json.dumps(result['claim_level_output'])}`",
                f"- Citation mapping: `{json.dumps(result['citation_handle_mapping'])}`",
                f"- Conflict preservation: `{json.dumps(result['conflict_preservation'])}`",
                f"- Lifecycle preservation: `{json.dumps(result['lifecycle_preservation'])}`",
                f"- Obligation evaluation: `{json.dumps(result['obligation_evaluation'])}`",
            ]
        )
    (ROOT / "evaluation" / "STEP11E_BUDGET6_SMOKE_TEST.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    write_artifacts()
