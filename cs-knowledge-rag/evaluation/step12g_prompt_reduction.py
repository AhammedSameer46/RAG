"""Diagnostic-only prompt reduction experiment for STEP 12G."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib import request

from cs_ingest.claim_answer_contract import validate_claim_answer
from cs_ingest.ollama_answer_generator import (
    _SYSTEM_PROMPT,
    _parse_response,
)

ROOT = Path(__file__).parents[1]
MODEL = "gemma3:4b"
BASE_URL = "http://localhost:11434"
TIMEOUT = 120.0
QUESTION_ID = "E014"


def _exact_context():
    prior = json.loads(
        (ROOT / "evaluation" / "step12f_prompt_isolation.json").read_text(
            encoding="utf-8"
        )
    )
    selected = json.loads(
        (ROOT / "evaluation" / "step12e_prompt_diagnostic.json").read_text(
            encoding="utf-8"
        )
    )
    return prior["variants"][0]["raw_ollama_response"], selected["model_facing_context"]


def _user_prompt(model_context):
    return "Model context (JSON):\n" + json.dumps(model_context, sort_keys=True)


def _remove(prompt: str, block: str) -> str:
    if block not in prompt:
        raise ValueError("Expected prompt block was not found.")
    return prompt.replace(block, "", 1)


def _variants():
    answer_plan_metadata = """- The Answer Plan is deterministic metadata describing how supplied evidence
  is organized; it is not factual evidence.
- Preserve every observation marked for separate preservation.
- Preserve every lifecycle distinction marked as required.
- Cite the underlying evidence handles, never the Answer Plan.
- If Answer Plan coverage is incomplete, do not invent missing information.
"""
    extra_formatting = """- Do not add extra top-level fields.
- Do not output markdown.
- Do not output prose outside the JSON object.
"""
    provenance_tail = """The application will deterministically attach exact provenance after generation.
"""
    g2 = _remove(_SYSTEM_PROMPT, answer_plan_metadata)
    g3 = _remove(_SYSTEM_PROMPT, extra_formatting)
    g6 = _f6_prompt()
    return [
        (
            "G1_FULL_PRODUCTION_BASELINE",
            "Exact failing F7 production configuration.",
            [],
            ["contract/schema", "grounding", "atomic-claims", "citations",
             "conflict/lifecycle", "Answer Plan/metadata", "formatting",
             "provenance"],
            _SYSTEM_PROMPT,
        ),
        (
            "G2_WITHOUT_ANSWER_PLAN_METADATA",
            "F7 with only explicit Answer Plan/metadata instructions removed.",
            ["Answer Plan/metadata"],
            ["contract/schema", "grounding", "atomic-claims", "citations",
             "conflict/lifecycle", "formatting", "provenance"],
            g2,
        ),
        (
            "G3_WITHOUT_EXTRA_FORMATTING",
            "F7 with only additional output-format restrictions removed.",
            ["extra formatting"],
            ["contract/schema", "grounding", "atomic-claims", "citations",
             "conflict/lifecycle", "Answer Plan/metadata", "provenance"],
            g3,
        ),
        (
            "G4_WITHOUT_META_RESTRICTIONS",
            "Not applicable: no distinct remaining meta/knowledge block exists beyond F6 groups and G2 metadata rules.",
            [],
            [],
            None,
        ),
        (
            "G5_WITHOUT_UNSUPPORTED_HANDLING",
            "Not applicable: insufficient-evidence and no-inference rules are already in the F6 grounding/contract groups.",
            [],
            [],
            None,
        ),
        (
            "G6_MINIMAL_REMAINING_PROMPT",
            "F6 instruction set plus the necessary response contract only.",
            [],
            ["contract/schema", "grounding", "atomic-claims", "citations",
             "conflict/lifecycle"],
            g6,
        ),
    ], provenance_tail


def _f6_prompt():
    return """You answer questions about institutional records.

Use ONLY the supplied evidence response.
Do not use outside knowledge.
Do not invent facts.
Do not infer unsupported facts.
Preserve conflicting source observations.
Every factual claim must be supported by the supplied evidence.

Return ONLY one JSON object with EXACTLY these three top-level fields:

{
  "status": "answered | insufficient_evidence | clarification_required",
  "claims": [
    {
      "text": "atomic factual claim",
      "citation_refs": ["E1", "E2"]
    }
  ]
}

Rules:

- The supplied evidence is authoritative for the answer.
- Every materially distinct supported observation relevant to the question
  MUST be represented in one or more atomic claims.
- Never collapse two source observations merely because they concern the same
  event, person, count, or other subject.
- If sources report different values, categories, or statuses, preserve both
  observations and attribute them separately.
- Related records across time MUST remain distinct unless the evidence
  explicitly states that they are the same record.
- Planning, meeting, status, and event lifecycle stages MUST NOT be collapsed.
- For an answerable question, status MUST be exactly "answered".
- For insufficient evidence, status MUST be exactly "insufficient_evidence".
- For a clarification request, status MUST be exactly "clarification_required".
- claims MUST be a non-empty array for status "answered".
- claims MUST be an empty array for status "insufficient_evidence" or "clarification_required".
- Each answered claim MUST contain non-empty text and at least one citation_ref.
- Every citation ref MUST exactly match a citation_ref handle supplied in the evidence context.
- Claims MUST be atomic; do not combine unrelated facts in one claim.
- Every factual claim must cite the evidence that directly supports that claim.
- Conflicting observations MUST remain separate, attributed claims; do not reconcile them.
- Do not merge planning, scheduling, and completion into one claim.
- Do not infer a relationship merely because records share a date, person,
  event name, or number.
- If evidence is insufficient, say so rather than filling gaps.
- Do not introduce information from model knowledge.
- Handles are the ONLY citation identifiers allowed.
- Never output source IDs, evidence IDs, filenames, or locations.
- Do not fabricate citation refs.
"""


def _run_variant(variant, user_prompt, selected):
    variant_id, description, removed, remaining, system_prompt = variant
    if system_prompt is None:
        return {
            "variant_id": variant_id,
            "description": description,
            "removed_instruction_groups": removed,
            "remaining_instruction_groups": remaining,
            "not_applicable": True,
            "system_prompt_character_count": 0,
            "user_prompt_character_count": len(user_prompt),
            "total_prompt_character_count": len(user_prompt),
            "http_status": None,
            "latency_seconds": 0,
            "raw_ollama_response": None,
            "parsed_inner_response": None,
            "contract_valid": None,
            "parser_or_contract_error": None,
            "response_character_count": 0,
        }
    payload = {
        "model": MODEL,
        "system": system_prompt,
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
        if error is None:
            try:
                validate_claim_answer(parsed, selected)
            except Exception as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    response_chars = len(raw or "")
    return {
        "variant_id": variant_id,
        "description": description,
        "removed_instruction_groups": removed,
        "remaining_instruction_groups": remaining,
        "system_prompt": system_prompt,
        "system_prompt_character_count": len(system_prompt),
        "user_prompt_character_count": len(user_prompt),
        "total_prompt_character_count": len(system_prompt) + len(user_prompt),
        "http_status": status,
        "latency_seconds": time.perf_counter() - started,
        "raw_ollama_response": raw,
        "parsed_inner_response": parsed,
        "contract_valid": error is None,
        "parser_or_contract_error": error,
        "response_character_count": response_chars,
    }


def _report(artifact):
    lines = [
        "# STEP 12G Prompt Reduction",
        "",
        "## Objective",
        "",
        "Isolate the remaining full-production-prompt failure observed in STEP 12F. This is a diagnostic experiment only.",
        "",
        "## STEP 12F findings",
        "",
        "F1-F6 were valid and F7 was invalid. The observed boundary was F6 → F7.",
        "",
        "## Actual remaining production-prompt blocks",
        "",
        "- Answer Plan/metadata instructions are explicit in the production prompt.",
        "- Additional output-format restrictions are explicit in the production prompt.",
        "- Model-knowledge and insufficient-evidence rules are already represented in the previously isolated grounding/contract groups; G4 and G5 are therefore not applicable.",
        "",
        "## G1-G6 configuration and results",
        "",
        "| Variant | Removed | System chars | HTTP | Contract valid | Error |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in artifact["variants"]:
        lines.append(
            f"| {item['variant_id']} | {', '.join(item['removed_instruction_groups']) or 'none'} | "
            f"{item['system_prompt_character_count']} | {item['http_status']} | "
            f"{item['contract_valid']} | {item['parser_or_contract_error']} |"
        )
    boundary = artifact["failure_boundary"]
    lines.extend(
        [
            "",
            "## First INVALID → VALID transition",
            "",
            f"- `{boundary['observed_transition'] or 'none'}`",
            "",
            "## Evidence-supported interpretation",
            "",
        ]
    )
    if boundary["first_valid_restoration"]:
        lines.append(
            f"- First validity restoration: `{boundary['first_valid_restoration']}`."
        )
    else:
        lines.append("- No validity restoration was observed.")
    lines.extend(
        [
            "- A specific prompt block is implicated only if removing that block restores validity while the exact G1 baseline is invalid.",
            "- If G2-G5 remain invalid and G6 is valid, no individual remaining block is isolated; the evidence supports an interaction or prompt-length/context-shape effect.",
            "",
            "## Smallest next controlled experiment",
            "",
            "Use the first observed restoration, if any, and split only that remaining block into smaller exact sub-blocks. If no individual removal restores validity, vary one prompt-length or context-shape factor while preserving the production instructions.",
        ]
    )
    (ROOT / "evaluation" / "STEP12G_PROMPT_REDUCTION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def run():
    _, model_context = _exact_context()
    selected = json.loads(
        (ROOT / "evaluation" / "step12e_prompt_diagnostic.json").read_text(
            encoding="utf-8")
    )
    selected_response = {
        "answer_context": selected["answer_context"],
        "answer_plan": selected["answer_plan"],
    }
    user_prompt = _user_prompt(model_context)
    variants, _ = _variants()
    results = [_run_variant(item, user_prompt, selected_response) for item in variants]
    first_valid = None
    previous_invalid = None
    for index, item in enumerate(results):
        if item["contract_valid"] is True and first_valid is None:
            first_valid = item["variant_id"]
            if index > 0 and results[index - 1]["contract_valid"] is False:
                previous_invalid = results[index - 1]["variant_id"]
    artifact = {
        "step": "12G",
        "question_id": QUESTION_ID,
        "model": MODEL,
        "timeout_seconds": TIMEOUT,
        "baseline_variant": "G1_FULL_PRODUCTION_BASELINE",
        "variants": results,
        "failure_boundary": {
            "first_valid_restoration": first_valid,
            "previous_invalid_variant": previous_invalid,
            "observed_transition": (
                f"{previous_invalid} → {first_valid}"
                if previous_invalid and first_valid
                else None
            ),
        },
    }
    (ROOT / "evaluation" / "step12g_prompt_reduction.json").write_text(
        json.dumps(artifact, indent=2) + "\n", encoding="utf-8"
    )
    _report(artifact)


if __name__ == "__main__":
    run()
