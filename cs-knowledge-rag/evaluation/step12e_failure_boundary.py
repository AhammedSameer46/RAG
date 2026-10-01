"""Diagnostic-only prompt and Ollama failure-boundary experiment for STEP 12E."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib import request

from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.answer_pipeline import _selected_evidence_response
from cs_ingest.citation_builder import citation_handles
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.evidence_selector import EvidenceSelector
from cs_ingest.ollama_answer_generator import (
    _SYSTEM_PROMPT,
    _model_answer_context,
    _parse_response,
    _user_prompt,
)
from cs_ingest.pipeline import QueryRetrievalPipeline

ROOT = Path(__file__).parents[1]
QUESTION_ID = "E014"
QUESTION = "What was reported about C-START participation?"
MODEL = "gemma3:4b"
BASE_URL = "http://localhost:11434"
TIMEOUT = 120.0


def _build_context():
    pipeline = QueryRetrievalPipeline.from_json(
        ROOT / "output" / "sample_normalized.json"
    )
    evidence_response = build_evidence_response(pipeline.run(QUESTION))
    selection = EvidenceSelector().select(
        QUESTION,
        evidence_response["query_understanding"],
        evidence_response,
        _selector_config(),
    )
    selected = _selected_evidence_response(evidence_response, selection)
    selected["answer_plan"] = build_answer_plan(selected)
    return selected


def _selector_config():
    from cs_ingest.evidence_selector import EvidenceSelectionConfig

    return EvidenceSelectionConfig(
        max_evidence_units=3,
        max_characters=12000,
        max_records=8,
        max_characters_per_unit=None,
    )


def _production_context(selected):
    return {
        "question": QUESTION,
        "answer_plan": selected["answer_plan"],
        "answer_context": _model_answer_context(selected),
    }


def _prompt_comparison(selected):
    step11b_context = {
        "question": QUESTION,
        "answer_context": _model_answer_context(selected),
    }
    step12c_context = _production_context(selected)
    return {
        "step11b_style": _context_stats(step11b_context),
        "step12c_style": _context_stats(step12c_context),
        "system_prompt": _prompt_stats(_SYSTEM_PROMPT),
        "notes": [
            "Step 11B-style user context omits the Answer Plan.",
            "Step 12C user context includes question, Answer Plan, and wrapped evidence.",
            "Counts are descriptive and do not establish a causal model failure.",
        ],
    }


def _context_stats(context):
    serialized = json.dumps(context, sort_keys=True)
    evidence_objects = sum(
        len(context["answer_context"].get(collection, []))
        for collection in ("supporting_evidence", "independent_evidence")
    )
    plan = context.get("answer_plan", {})
    return {
        "character_count": len(serialized),
        "evidence_object_count": evidence_objects,
        "answer_plan_observation_count": len(plan.get("observations", [])),
        "conflict_group_count": len(plan.get("conflict_groups", [])),
        "lifecycle_group_count": len(plan.get("lifecycle_groups", [])),
        "citation_handle_count": evidence_objects,
        "max_nesting_depth": _max_depth(context),
        "serialized_context": serialized,
    }


def _prompt_stats(prompt):
    return {
        "character_count": len(prompt),
        "instruction_count": sum(
            1 for line in prompt.splitlines() if line.lstrip().startswith("- ")
        ),
    }


def _max_depth(value, depth=0):
    if isinstance(value, dict):
        return max([depth] + [_max_depth(item, depth + 1) for item in value.values()])
    if isinstance(value, list):
        return max([depth] + [_max_depth(item, depth + 1) for item in value])
    return depth


def build_offline_artifacts():
    selected = _build_context()
    production_context = _production_context(selected)
    model_user_prompt = _user_prompt(QUESTION, selected)
    diagnostic = {
        "question_id": QUESTION_ID,
        "question": QUESTION,
        "selected_evidence_ids": selected["selection"]["selected_evidence_ids"],
        "selected_evidence_count": len(
            selected["answer_context"]["supporting_evidence"]
        )
        + len(selected["answer_context"]["independent_evidence"]),
        "truncated": selected["selection"]["truncated"],
        "answer_plan": selected["answer_plan"],
        "answer_context": selected["answer_context"],
        "model_facing_context": production_context,
        "system_prompt": _SYSTEM_PROMPT,
        "user_prompt": model_user_prompt,
        "total_prompt_character_count": len(_SYSTEM_PROMPT) + len(model_user_prompt),
        "system_prompt_character_count": len(_SYSTEM_PROMPT),
        "user_prompt_character_count": len(model_user_prompt),
        "answer_plan_character_count": len(
            json.dumps(selected["answer_plan"], sort_keys=True)
        ),
        "answer_context_character_count": len(
            json.dumps(selected["answer_context"], sort_keys=True)
        ),
    }
    comparison = _prompt_comparison(selected)
    (ROOT / "evaluation" / "step12e_prompt_diagnostic.json").write_text(
        json.dumps(diagnostic, indent=2) + "\n", encoding="utf-8"
    )
    _write_comparison(comparison)
    return selected


def _write_comparison(comparison):
    a = comparison["step11b_style"]
    b = comparison["step12c_style"]
    lines = [
        "# STEP 12E Prompt Comparison",
        "",
        "This is a descriptive offline comparison. No Ollama request is made by this section.",
        "",
        "| Metric | Step 11B-style | Step 12C |",
        "|---|---:|---:|",
        f"| Context characters | {a['character_count']} | {b['character_count']} |",
        f"| Evidence objects | {a['evidence_object_count']} | {b['evidence_object_count']} |",
        f"| Answer Plan observations | {a['answer_plan_observation_count']} | {b['answer_plan_observation_count']} |",
        f"| Conflict groups | {a['conflict_group_count']} | {b['conflict_group_count']} |",
        f"| Lifecycle groups | {a['lifecycle_group_count']} | {b['lifecycle_group_count']} |",
        f"| Citation handles | {a['citation_handle_count']} | {b['citation_handle_count']} |",
        f"| Maximum nesting depth | {a['max_nesting_depth']} | {b['max_nesting_depth']} |",
        "",
        "## Prompt instructions",
        "",
        f"- Production system prompt characters: {comparison['system_prompt']['character_count']}",
        f"- Production system prompt bullet instructions: {comparison['system_prompt']['instruction_count']}",
        "",
        "## Duplication and structure",
        "",
        "- Evidence objects are the same selected wrapped evidence in both contexts.",
        "- Step 12C adds deterministic plan metadata; it does not replace evidence.",
        "- Provenance remains inside each evidence object and is not copied into claims.",
        "- The plan contains evidence IDs and provenance references, so some identifiers are repeated between plan metadata and evidence objects.",
        "- Conflict and lifecycle group membership is represented in the plan in addition to the underlying evidence text.",
        "- No causal conclusion is drawn from these structural differences.",
    ]
    (ROOT / "evaluation" / "STEP12E_PROMPT_COMPARISON.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _schema_system():
    return (
        'Return ONLY JSON with exactly {"status":"answered","claims":[{"text":"test",'
        '"citation_refs":["E1"]}]} and no other fields.'
    )


def _diagnostic_prompts(selected):
    evidence = _model_answer_context(selected)
    plan = selected["answer_plan"]
    return {
        "D1": (_schema_system(), "Produce the required test response."),
        "D2": (
            _schema_system(),
            f"Question: {QUESTION}\nProduce the required test response.",
        ),
        "D3": (
            _schema_system(),
            "Question: "
            + QUESTION
            + "\nEvidence context (JSON):\n"
            + json.dumps(evidence, sort_keys=True),
        ),
        "D4": (
            _schema_system(),
            "Question: "
            + QUESTION
            + "\nAnswer Plan (JSON):\n"
            + json.dumps(plan, sort_keys=True),
        ),
        "D5": (_SYSTEM_PROMPT, _user_prompt(QUESTION, selected)),
    }


def _contract_result(parsed):
    if not isinstance(parsed, dict) or set(parsed) != {"status", "claims"}:
        return False
    if parsed.get("status") != "answered" or not isinstance(parsed.get("claims"), list):
        return False
    return bool(parsed["claims"]) and all(
        isinstance(claim, dict)
        and set(claim) == {"text", "citation_refs"}
        and isinstance(claim["text"], str)
        and isinstance(claim["citation_refs"], list)
        and all(isinstance(ref, str) for ref in claim["citation_refs"])
        for claim in parsed["claims"]
    )


def run_diagnostics(selected):
    results = []
    for diagnostic_id, (system, prompt) in _diagnostic_prompts(selected).items():
        payload = {
            "model": MODEL,
            "system": system,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }
        started = time.perf_counter()
        http_status = None
        raw_response = None
        parsed = None
        error = None
        try:
            body = json.dumps(payload).encode("utf-8")
            http_request = request.Request(
                f"{BASE_URL}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(http_request, timeout=TIMEOUT) as response:
                http_status = getattr(response, "status", None)
                raw_bytes = response.read()
            raw_response = raw_bytes.decode("utf-8", errors="replace")
            try:
                parsed = _parse_response(raw_bytes)
            except Exception as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
        results.append(
            {
                "diagnostic_id": diagnostic_id,
                "prompt_character_count": len(prompt),
                "system_prompt_character_count": len(system),
                "http_status": http_status,
                "latency_seconds": time.perf_counter() - started,
                "raw_ollama_response": raw_response,
                "parsed_response": parsed,
                "parser_or_contract_error": error,
                "response_character_count": len(raw_response or ""),
                "satisfies_claim_level_contract": _contract_result(parsed),
            }
        )
    return results


def _write_failure_report(results, comparison):
    lines = [
        "# STEP 12E Failure Boundary",
        "",
        "## Diagnostic scope",
        "",
        "D1–D5 are isolated diagnostic requests, not evaluation attempts. No E001/E006/E014/E016/E017 question was rerun.",
        "",
        "| ID | Prompt chars | HTTP | Latency | Contract | Parser/contract error |",
        "|---|---:|---:|---:|---|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['diagnostic_id']} | {item['prompt_character_count']} | "
            f"{item['http_status']} | {item['latency_seconds']:.3f}s | "
            f"{item['satisfies_claim_level_contract']} | "
            f"{item['parser_or_contract_error']} |"
        )
    statuses = [item["satisfies_claim_level_contract"] for item in results]
    boundary = "no deterministic boundary observed"
    for left, right, label in zip(statuses, statuses[1:], ("D1 → D2", "D2 → D3", "D3 → D4", "D4 → D5")):
        if left and not right:
            boundary = f"{label}: first observed valid-to-invalid transition"
            break
    lines.extend(
        [
            "",
            "## Observed boundary",
            "",
            f"- Result: **{boundary}**",
            f"- Contract-valid sequence: `{statuses}`",
            "- This conclusion uses only the recorded diagnostic responses.",
            "",
            "## Interpretation",
            "",
            "- Answer Plan implicated: "
            + ("yes, if the first transition is D3 → D4." if boundary.startswith("D3") else "not established by the observed sequence."),
            "- Parser implicated: "
            + ("yes, only if raw output is structurally valid but parsed as invalid." if any(
                item["raw_ollama_response"] and item["parsed_response"] is None
                and item["parser_or_contract_error"] for item in results
            ) else "not established as a separate defect."),
            "- Full production prompt/context implicated: "
            + ("yes, if the first transition is D4 → D5." if boundary.startswith("D4") else "not established by the observed sequence."),
            "",
            "## Next smallest controlled experiment",
            "",
            "Use the earliest observed transition only, with one narrowly varied payload at that boundary; preserve the same model, timeout, and single-attempt rule. Do not change production code until that experiment identifies a reproducible cause.",
        ]
    )
    (ROOT / "evaluation" / "STEP12E_FAILURE_BOUNDARY.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main():
    selected = build_offline_artifacts()
    results = run_diagnostics(selected)
    artifact = {
        "diagnostic_config": {
            "model": MODEL,
            "base_url": BASE_URL,
            "timeout": TIMEOUT,
            "diagnostic_ids": ["D1", "D2", "D3", "D4", "D5"],
            "evaluation_attempts": 0,
        },
        "results": results,
    }
    (ROOT / "evaluation" / "step12e_failure_boundary.json").write_text(
        json.dumps(artifact, indent=2) + "\n", encoding="utf-8"
    )
    comparison = json.loads(
        (ROOT / "evaluation" / "step12e_prompt_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )
    _write_failure_report(results, comparison)


if __name__ == "__main__":
    main()
