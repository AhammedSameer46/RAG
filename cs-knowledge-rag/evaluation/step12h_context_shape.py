"""Diagnostic-only context-shape experiment for STEP 12H."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib import request

from cs_ingest.ollama_answer_generator import _parse_response

ROOT = Path(__file__).parents[1]
MODEL = "gemma3:4b"
BASE_URL = "http://localhost:11434"
TIMEOUT = 120.0
QUESTION_ID = "E014"


def _load():
    diagnostic = json.loads(
        (ROOT / "evaluation" / "step12e_prompt_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )
    return diagnostic["question"], diagnostic["answer_plan"], diagnostic["answer_context"]


def _schema():
    return (
        'Return ONLY JSON with exactly {"status":"answered","claims":[{"text":"test",'
        '"citation_refs":["E1"]}]} and no other fields.'
    )


def _evidence_objects(answer_context):
    return [
        {"citation_ref": f"E{index}", "evidence": evidence}
        for index, evidence in enumerate(
            answer_context.get("supporting_evidence", [])
            + answer_context.get("independent_evidence", []),
            start=1,
        )
    ]


def _compact_plan(plan):
    observations = []
    for observation in plan.get("observations", []):
        observations.append(
            {
                "observation_id": observation.get("observation_id"),
                "evidence_ids": observation.get("evidence_ids", []),
                "preserve_separately": observation.get("preserve_separately"),
            }
        )
    return {
        "answerability": plan.get("answerability"),
        "observations": observations,
        "conflict_groups": [
            {
                "group_id": group.get("group_id"),
                "evidence_ids": group.get("evidence_ids", []),
                "preserve_separately": group.get("preserve_separately"),
            }
            for group in plan.get("conflict_groups", [])
        ],
        "lifecycle_groups": [
            {
                "group_id": group.get("group_id"),
                "evidence_ids": group.get("evidence_ids", []),
                "preserve_separately": group.get("preserve_separately"),
            }
            for group in plan.get("lifecycle_groups", [])
        ],
        "coverage": plan.get("coverage", {}),
    }


def _flat_evidence(answer_context):
    flat = []
    for item in _evidence_objects(answer_context):
        evidence = dict(item["evidence"])
        flat.append({"citation_ref": item["citation_ref"], **evidence})
    return flat


def _compact_evidence(answer_context):
    compact = []
    for item in _evidence_objects(answer_context):
        evidence = dict(item["evidence"])
        compact.append(
            {
                "citation_ref": item["citation_ref"],
                "evidence_id": evidence.get("evidence_id"),
                "source_id": evidence.get("source_id"),
                "filename": evidence.get("filename"),
                "location": {
                    key: evidence[key]
                    for key in ("page", "sheet", "row", "cell", "cell_range")
                    if key in evidence
                },
                "evidence_text": evidence.get("text"),
                "raw_values": {
                    key: value
                    for key, value in evidence.items()
                    if key not in {
                        "evidence_id", "source_id", "filename", "text",
                        "page", "sheet", "row", "cell", "cell_range",
                    }
                },
            }
        )
    return compact


def _contexts(question, plan, answer_context):
    evidence = _evidence_objects(answer_context)
    compact_plan = _compact_plan(plan)
    compact_evidence = _compact_evidence(answer_context)
    flat_evidence = _flat_evidence(answer_context)
    return [
        (
            "H1_D4_BASELINE",
            "Exact successful STEP 12E D4 serialization: question plus full Answer Plan.",
            "question_plus_full_answer_plan",
            "Question: " + question + "\nAnswer Plan (JSON):\n"
            + json.dumps(plan, sort_keys=True),
            plan,
            [],
        ),
        (
            "H2_EVIDENCE_ONLY",
            "Question plus exact selected evidence, with Answer Plan removed.",
            "question_plus_evidence",
            "Question: " + question + "\nEvidence context (JSON):\n"
            + json.dumps(evidence, sort_keys=True),
            {},
            evidence,
        ),
        (
            "H3_COMPACT_ANSWER_PLAN",
            "Question, compact Answer Plan, and exact selected evidence.",
            "question_plus_compact_plan_plus_evidence",
            "Question: " + question + "\nAnswer Plan (JSON):\n"
            + json.dumps(compact_plan, sort_keys=True)
            + "\nEvidence context (JSON):\n"
            + json.dumps(evidence, sort_keys=True),
            compact_plan,
            evidence,
        ),
        (
            "H4_COMPACT_EVIDENCE_WRAPPER",
            "Question, full Answer Plan, and flattened compact evidence wrappers.",
            "question_plus_full_plan_plus_compact_evidence",
            "Question: " + question + "\nAnswer Plan (JSON):\n"
            + json.dumps(plan, sort_keys=True)
            + "\nEvidence context (JSON):\n"
            + json.dumps(compact_evidence, sort_keys=True),
            plan,
            compact_evidence,
        ),
        (
            "H5_COMPACT_CONTEXT",
            "Question, compact Answer Plan, and compact evidence wrappers.",
            "question_plus_compact_plan_plus_compact_evidence",
            "Question: " + question + "\nAnswer Plan (JSON):\n"
            + json.dumps(compact_plan, sort_keys=True)
            + "\nEvidence context (JSON):\n"
            + json.dumps(compact_evidence, sort_keys=True),
            compact_plan,
            compact_evidence,
        ),
        (
            "H6_FLAT_CONTEXT",
            "Question, compact Answer Plan, and flat evidence list.",
            "question_plus_compact_plan_plus_flat_evidence",
            "Question: " + question + "\nAnswer Plan (JSON):\n"
            + json.dumps(compact_plan, sort_keys=True)
            + "\nEvidence (JSON list):\n"
            + json.dumps(flat_evidence, sort_keys=True),
            compact_plan,
            flat_evidence,
        ),
        (
            "H7_PLAIN_TEXT_CONTEXT",
            "Question and equivalent plain-text context.",
            "plain_text",
            _plain_text(question, compact_plan, flat_evidence),
            compact_plan,
            flat_evidence,
        ),
    ]


def _plain_text(question, plan, evidence):
    lines = ["Question:", question, "", "Answer-plan requirements:"]
    for observation in plan.get("observations", []):
        lines.append(
            "- Observation "
            + str(observation.get("observation_id"))
            + "; evidence IDs "
            + ", ".join(observation.get("evidence_ids", []))
            + "; preserve separately="
            + str(observation.get("preserve_separately"))
        )
    lines.extend(["", "Evidence:"])
    for item in evidence:
        lines.extend(
            [
                "Evidence " + str(item.get("citation_ref")) + ":",
                json.dumps(item, sort_keys=True),
            ]
        )
    lines.extend(["", "Citation handles: E1, E2, E3"])
    return "\n".join(lines)


def _depth(value, depth=0):
    if isinstance(value, dict):
        return max([depth] + [_depth(item, depth + 1) for item in value.values()])
    if isinstance(value, list):
        return max([depth] + [_depth(item, depth + 1) for item in value])
    return depth


def _valid(parsed):
    return (
        isinstance(parsed, dict)
        and set(parsed) == {"status", "claims"}
        and parsed.get("status")
        in {"answered", "insufficient_evidence", "clarification_required"}
        and isinstance(parsed.get("claims"), list)
        and (
            parsed["status"] != "answered"
            or bool(parsed["claims"])
        )
        and all(
            isinstance(claim, dict)
            and set(claim) == {"text", "citation_refs"}
            and isinstance(claim["text"], str)
            and isinstance(claim["citation_refs"], list)
            and bool(claim["citation_refs"])
            and all(isinstance(ref, str) for ref in claim["citation_refs"])
            for claim in parsed["claims"]
        )
    )


def _run_variant(item, question, plan, answer_context):
    variant_id, description, representation, user_prompt, plan_value, evidence_value = item
    plan_json = json.dumps(plan_value, sort_keys=True)
    evidence_json = json.dumps(evidence_value, sort_keys=True)
    payload = {
        "model": MODEL,
        "system": _schema(),
        "prompt": user_prompt,
        "format": "json",
        "stream": False,
    }
    started = time.perf_counter()
    status = None
    raw = None
    parsed = None
    error = None
    try:
        req = request.Request(
            f"{BASE_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=TIMEOUT) as response:
            status = getattr(response, "status", None)
            body = response.read()
        raw = body.decode("utf-8", errors="replace")
        try:
            parsed = _parse_response(body)
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    return {
        "variant_id": variant_id,
        "description": description,
        "context_representation": representation,
        "question_characters": len(question),
        "answer_plan_characters": len(plan_json),
        "evidence_characters": len(evidence_json),
        "total_context_characters": len(user_prompt),
        "max_nesting_depth": _depth({"answer_plan": plan_value, "evidence": evidence_value}),
        "evidence_object_count": len(evidence_value),
        "answer_plan_observation_count": len(plan_value.get("observations", [])),
        "citation_handle_count": len(
            {item.get("citation_ref") for item in evidence_value if isinstance(item, dict)}
        ),
        "http_status": status,
        "latency_seconds": time.perf_counter() - started,
        "raw_ollama_response": raw,
        "parsed_inner_response": parsed,
        "response_characters": len(raw or ""),
        "contract_valid": _valid(parsed),
        "parser_or_contract_error": error,
    }


def _report(artifact):
    lines = [
        "# STEP 12H Context Shape",
        "",
        "## Objective",
        "",
        "Determine whether a structural feature of the E014 model-facing context changes Gemma3:4b claim-level contract validity. This is diagnostic only.",
        "",
        "## Baseline findings",
        "",
        "- STEP 12E: D1-D4 valid, D5 invalid.",
        "- STEP 12F: F1-F6 valid, F7 invalid.",
        "- STEP 12G: G1, G2, G3, and G6 invalid.",
        "",
        "## Representation and equivalence",
        "",
        "All variants use the same E014 question and the same selected evidence values. Compact forms retain observation/evidence IDs, citation handles, source identity, locations, and evidence values. Only serialization and nesting change.",
        "",
        "## Results",
        "",
        "| Variant | Representation | Context chars | Depth | Evidence objects | Plan observations | HTTP | Contract | Error |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in artifact["variants"]:
        lines.append(
            f"| {item['variant_id']} | {item['context_representation']} | "
            f"{item['total_context_characters']} | {item['max_nesting_depth']} | "
            f"{item['evidence_object_count']} | {item['answer_plan_observation_count']} | "
            f"{item['http_status']} | {item['contract_valid']} | "
            f"{item['parser_or_contract_error']} |"
        )
    lines.extend(
        [
            "",
            "## First transition",
            "",
            "- The first transition is recorded from the observed sequence only; no causal conclusion is made from a single run.",
            "",
            "## Interpretation",
            "",
            "Interpretation is limited to contract validity. If compact representations remain invalid or results vary across equivalent representations, no deterministic context-shape boundary is established and model/output instability remains a hypothesis.",
        ]
    )
    (ROOT / "evaluation" / "STEP12H_CONTEXT_SHAPE.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def run():
    question, plan, answer_context = _load()
    results = [
        _run_variant(item, question, plan, answer_context)
        for item in _contexts(question, plan, answer_context)
    ]
    first_valid = None
    previous_invalid = None
    first_invalid = None
    previous_valid = None
    for index, item in enumerate(results):
        if item["contract_valid"] and first_valid is None:
            first_valid = item["variant_id"]
            if index > 0 and not results[index - 1]["contract_valid"]:
                previous_invalid = results[index - 1]["variant_id"]
        if not item["contract_valid"] and first_invalid is None:
            first_invalid = item["variant_id"]
            if index > 0 and results[index - 1]["contract_valid"]:
                previous_valid = results[index - 1]["variant_id"]
    artifact = {
        "step": "12H",
        "question_id": QUESTION_ID,
        "model": MODEL,
        "timeout_seconds": TIMEOUT,
        "variants": results,
        "transitions": {
            "first_invalid_variant": first_invalid,
            "previous_valid_variant": previous_valid,
            "first_valid_restoration": first_valid,
            "previous_invalid_variant": previous_invalid,
        },
    }
    (ROOT / "evaluation" / "step12h_context_shape.json").write_text(
        json.dumps(artifact, indent=2) + "\n", encoding="utf-8"
    )
    _report(artifact)


if __name__ == "__main__":
    run()
