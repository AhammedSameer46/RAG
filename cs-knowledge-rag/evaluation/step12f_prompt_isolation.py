"""STEP 12F diagnostic isolation of the production prompt boundary."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib import request

from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.answer_pipeline import _selected_evidence_response
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.ollama_answer_generator import (
    _SYSTEM_PROMPT,
    _model_answer_context,
    _parse_response,
)
from cs_ingest.pipeline import QueryRetrievalPipeline

ROOT = Path(__file__).parents[1]
QUESTION_ID = "E014"
QUESTION = "What was reported about C-START participation?"
MODEL = "gemma3:4b"
BASE_URL = "http://localhost:11434"
TIMEOUT = 120.0


def _selected_response():
    pipeline = QueryRetrievalPipeline.from_json(
        ROOT / "output" / "sample_normalized.json"
    )
    response = build_evidence_response(pipeline.run(QUESTION))
    selection = EvidenceSelector().select(
        QUESTION,
        response["query_understanding"],
        response,
        EvidenceSelectionConfig(
            max_evidence_units=3,
            max_characters=12000,
            max_records=8,
            max_characters_per_unit=None,
        ),
    )
    selected = _selected_evidence_response(response, selection)
    selected["answer_plan"] = build_answer_plan(selected)
    return selected


def _schema():
    return """Return ONLY one JSON object with EXACTLY these three top-level fields:

{
  "status": "answered | insufficient_evidence | clarification_required",
  "claims": [
    {
      "text": "atomic factual claim",
      "citation_refs": ["E1", "E2"]
    }
  ]
}"""


def _groups():
    return {
        "contract/schema": _schema()
        + """

Rules:
- For an answerable question, status MUST be exactly "answered".
- For insufficient evidence, status MUST be exactly "insufficient_evidence".
- For a clarification request, status MUST be exactly "clarification_required".
- claims MUST be a non-empty array for status "answered".
- claims MUST be an empty array for status "insufficient_evidence" or "clarification_required".
- Each answered claim MUST contain non-empty text and at least one citation_ref.
- Do not add extra top-level fields.
- Do not output markdown.
- Do not output prose outside the JSON object.""",
        "evidence-grounding": """Use ONLY the supplied evidence response.
Do not use outside knowledge.
Do not invent facts.
Do not infer unsupported facts.
Every factual claim must be supported by the supplied evidence.

Rules:
- The supplied evidence is authoritative for the answer.
- If evidence is insufficient, say so rather than filling gaps.
- Do not introduce information from model knowledge.""",
        "atomic-claims": """Rules:
- Every materially distinct supported observation relevant to the question MUST be represented in one or more atomic claims.
- Never collapse two source observations merely because they concern the same event, person, count, or other subject.
- Claims MUST be atomic; do not combine unrelated facts in one claim.""",
        "citations": """Rules:
- Every citation ref MUST exactly match a citation_ref handle supplied in the evidence context.
- Every factual claim must cite the evidence that directly supports that claim.
- Handles are the ONLY citation identifiers allowed.
- Never output source IDs, evidence IDs, filenames, or locations.
- Do not fabricate citation refs.""",
        "conflict/lifecycle": """Rules:
- Preserve conflicting source observations.
- If sources report different values, categories, or statuses, preserve both observations and attribute them separately.
- Related records across time MUST remain distinct unless the evidence explicitly states that they are the same record.
- Planning, meeting, status, and event lifecycle stages MUST NOT be collapsed.
- Conflicting observations MUST remain separate, attributed claims; do not reconcile them.
- Do not merge planning, scheduling, and completion into one claim.
- Do not infer a relationship merely because records share a date, person, event name, or number.""",
        "other-production": """Rules:
- The Answer Plan is deterministic metadata describing how supplied evidence is organized; it is not factual evidence.
- Preserve every observation marked for separate preservation.
- Preserve every lifecycle distinction marked as required.
- Cite the underlying evidence handles, never the Answer Plan.
- If Answer Plan coverage is incomplete, do not invent missing information.
- Do not add confidence.
- Do not add query_understanding.
- Do not add sources.
- Do not add selection metadata.

The application will deterministically attach exact provenance after generation.""",
    }


def _systems():
    groups = _groups()
    ordered = [
        ("contract/schema",),
        ("contract/schema", "evidence-grounding"),
        ("contract/schema", "evidence-grounding", "atomic-claims"),
        ("contract/schema", "evidence-grounding", "atomic-claims", "citations"),
        (
            "contract/schema",
            "evidence-grounding",
            "atomic-claims",
            "citations",
            "conflict/lifecycle",
        ),
    ]
    systems = {
        "F1_D4_BASELINE": _schema(),
        "F2_CONTRACT_SCHEMA": groups["contract/schema"],
        "F3_GROUNDING": "\n\n".join(
            groups[name] for name in ordered[1]
        ),
        "F4_ATOMIC_CLAIMS": "\n\n".join(
            groups[name] for name in ordered[2]
        ),
        "F5_CITATIONS": "\n\n".join(
            groups[name] for name in ordered[3]
        ),
        "F6_CONFLICT_LIFECYCLE": "\n\n".join(
            groups[name] for name in ordered[4]
        ),
    }
    systems["F7_FULL_PRODUCTION_PROMPT"] = _SYSTEM_PROMPT
    # Preserve requested ordering explicitly.
    return [
        ("F1_D4_BASELINE", systems["F1_D4_BASELINE"], ["baseline_schema_only"]),
        ("F2_CONTRACT_SCHEMA", systems["F2_CONTRACT_SCHEMA"], ["contract/schema"]),
        ("F3_GROUNDING", systems["F3_GROUNDING"], ["contract/schema", "evidence-grounding"]),
        ("F4_ATOMIC_CLAIMS", systems["F4_ATOMIC_CLAIMS"], ["contract/schema", "evidence-grounding", "atomic-claims"]),
        ("F5_CITATIONS", systems["F5_CITATIONS"], ["contract/schema", "evidence-grounding", "atomic-claims", "citations"]),
        ("F6_CONFLICT_LIFECYCLE", systems["F6_CONFLICT_LIFECYCLE"], ["contract/schema", "evidence-grounding", "atomic-claims", "citations", "conflict/lifecycle"]),
        ("F7_FULL_PRODUCTION_PROMPT", systems["F7_FULL_PRODUCTION_PROMPT"], ["all production groups"]),
    ]


def _user_prompt(selected):
    # Exact successful D4 user side from STEP 12E: question plus Answer Plan.
    return (
        "Question: "
        + QUESTION
        + "\nAnswer Plan (JSON):\n"
        + json.dumps(selected["answer_plan"], sort_keys=True)
    )


def _production_context(selected):
    return {
        "question": QUESTION,
        "answer_plan": selected["answer_plan"],
        "answer_context": _model_answer_context(selected),
    }


def _production_user_prompt(selected):
    return _user_prompt_from_production_context(
        _production_context(selected)
    )


def _user_prompt_from_production_context(context):
    return "Model context (JSON):\n" + json.dumps(context, sort_keys=True)


def _valid(parsed):
    return (
        isinstance(parsed, dict)
        and set(parsed) == {"status", "claims"}
        and parsed.get("status") in {"answered", "insufficient_evidence", "clarification_required"}
        and isinstance(parsed.get("claims"), list)
        and (
            parsed["status"] != "answered"
            or (
                bool(parsed["claims"])
                and all(
                    isinstance(claim, dict)
                    and set(claim) == {"text", "citation_refs"}
                    and isinstance(claim["text"], str)
                    and isinstance(claim["citation_refs"], list)
                    for claim in parsed["claims"]
                )
            )
        )
    )


def run():
    selected = _selected_response()
    variants = []
    for variant_id, system_prompt, instruction_groups in _systems():
        user_prompt = (
            _production_user_prompt(selected)
            if variant_id == "F7_FULL_PRODUCTION_PROMPT"
            else _user_prompt(selected)
        )
        payload = {
            "model": MODEL,
            "system": system_prompt,
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
        }
        started = time.perf_counter()
        http_status = None
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
                http_status = getattr(response, "status", None)
                body = response.read()
            raw = body.decode("utf-8", errors="replace")
            try:
                parsed = _parse_response(body)
            except Exception as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
        except Exception as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
        variants.append(
            {
                "variant_id": variant_id,
                "description": variant_id,
                "instruction_groups": instruction_groups,
                "prompt_character_count": len(user_prompt),
                "system_prompt_character_count": len(system_prompt),
                "http_status": http_status,
                "latency_seconds": time.perf_counter() - started,
                "raw_ollama_response": raw,
                "parsed_inner_response": parsed,
                "contract_valid": _valid(parsed),
                "parser_or_contract_error": error,
            }
        )
    first_invalid = None
    previous_valid = None
    for index, item in enumerate(variants):
        if not item["contract_valid"] and first_invalid is None:
            first_invalid = item["variant_id"]
            if index > 0 and variants[index - 1]["contract_valid"]:
                previous_valid = variants[index - 1]["variant_id"]
    artifact = {
        "step": "12F",
        "question_id": QUESTION_ID,
        "model": MODEL,
        "timeout_seconds": TIMEOUT,
        "variants": variants,
        "failure_boundary": {
            "first_invalid_variant": first_invalid,
            "previous_valid_variant": previous_valid if first_invalid else None,
            "observed_transition": (
                f"{previous_valid} → {first_invalid}" if first_invalid else "none"
            ),
        },
    }
    (ROOT / "evaluation" / "step12f_prompt_isolation.json").write_text(
        json.dumps(artifact, indent=2) + "\n", encoding="utf-8"
    )
    _report(artifact)


def _report(artifact):
    lines = [
        "# STEP 12F Prompt Isolation",
        "",
        "## Objective",
        "",
        "Isolate the D4 → D5 production-prompt failure boundary using the same E014 Answer Plan reconstruction. These are diagnostic requests, not evaluation attempts.",
        "",
        "## STEP 12E baseline",
        "",
        "- D1: VALID",
        "- D2: VALID",
        "- D3: VALID",
        "- D4: VALID",
        "- D5: INVALID",
        "",
        "## Actual production instruction groups",
        "",
        "The variants use these groups extracted from the current production prompt: contract/schema, evidence-grounding, atomic claims, citations, conflict/lifecycle, and other production formatting/Answer Plan rules. F7 uses the exact production prompt.",
        "",
        "## F1–F7 results",
        "",
        "| Variant | Prompt chars | HTTP | Latency | Contract valid | Error |",
        "|---|---:|---:|---:|---|---|",
    ]
    for item in artifact["variants"]:
        lines.append(
            f"| {item['variant_id']} | {item['prompt_character_count']} | {item['http_status']} | "
            f"{item['latency_seconds']:.3f}s | {item['contract_valid']} | {item['parser_or_contract_error']} |"
        )
    boundary = artifact["failure_boundary"]["observed_transition"]
    lines.extend(
        [
            "",
            "## First observed valid → invalid transition",
            "",
            f"- `{boundary}`",
            "",
            "## Raw failure modes",
            "",
        ]
    )
    for item in artifact["variants"]:
        if not item["contract_valid"]:
            lines.append(
                f"- **{item['variant_id']}**: `{item['parser_or_contract_error']}`. "
                "The raw response was retained in the JSON artifact."
            )
    lines.extend(
        [
            "",
            "## Evidence-supported interpretation",
            "",
            "- Contract instructions as the cause: not established unless F2 is the first invalid variant.",
            "- Grounding instructions as the cause: not established unless F3 is the first invalid variant.",
            "- Atomic-claim instructions as the cause: not established unless F4 is the first invalid variant.",
            "- Citation instructions as the cause: not established unless F5 is the first invalid variant.",
            "- Conflict/lifecycle instructions as the cause: not established unless F6 is the first invalid variant.",
            "- Full prompt interaction: supported only if F1–F6 are valid and F7 is invalid.",
            "- No isolated cause: supported if the sequence does not isolate one accumulated group.",
            "",
            "## Next smallest controlled experiment",
            "",
            "Use only the earliest observed transition, if any, and vary one production instruction group or formatting block at that boundary. Preserve the model, context, timeout, and single-attempt rule.",
        ]
    )
    (ROOT / "evaluation" / "STEP12F_PROMPT_ISOLATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    run()
