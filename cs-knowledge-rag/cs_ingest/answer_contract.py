"""Deterministic validation contract for future evidence-grounded answers."""

from __future__ import annotations

from typing import Any

_ANSWER_STATUSES = {"answered", "insufficient_evidence", "clarification_required"}
_EVIDENCE_ROLES = (
    ("supporting_evidence", "supporting"),
    ("independent_evidence", "independent"),
)
_LOCATION_FIELDS = {
    "page",
    "sheet",
    "row",
    "cell",
    "cell_range",
}


def validate_answer(
    answer: dict[str, Any], evidence_response: dict[str, Any]
) -> dict[str, Any]:
    """Validate answer structure and exact grounding against an evidence response."""
    errors: list[dict[str, str]] = []
    if not isinstance(answer, dict):
        return _result("INVALID_ANSWER", "Answer must be an object.")
    if not isinstance(evidence_response, dict):
        return _result("INVALID_EVIDENCE_RESPONSE", "Evidence response must be an object.")

    answer_status = answer.get("status")
    response_status = evidence_response.get("status")
    if answer_status not in _ANSWER_STATUSES:
        errors.append(_error("INVALID_STATUS", "Answer status is not supported."))
    expected_status = {
        "answerable": "answered",
        "insufficient_evidence": "insufficient_evidence",
        "clarification_required": "clarification_required",
    }.get(response_status)
    if expected_status is None or answer_status != expected_status:
        errors.append(
            _error(
                "STATUS_MISMATCH",
                "Answer status does not match the evidence response status.",
            )
        )

    answer_text = answer.get("answer")
    citations = answer.get("citations")
    if not isinstance(answer_text, str):
        errors.append(_error("INVALID_ANSWER_TEXT", "Answer must be text."))
        answer_text = ""
    if not isinstance(citations, list):
        errors.append(_error("INVALID_CITATIONS", "Citations must be a list."))
        citations = []

    if answer_status == "answered":
        if not answer_text.strip():
            errors.append(_error("EMPTY_ANSWER", "Answered responses require answer text."))
        if not citations:
            errors.append(_error("NO_CITATIONS", "Answered responses require a citation."))
    elif answer_status in {"insufficient_evidence", "clarification_required"}:
        if answer_text.strip():
            errors.append(
                _error(
                    "FACTUAL_ANSWER_NOT_ALLOWED",
                    f"{answer_status} responses must not contain an answer.",
                )
            )
        if citations:
            errors.append(
                _error(
                    "CITATIONS_NOT_ALLOWED",
                    f"{answer_status} responses must not contain citations.",
                )
            )

    evidence_by_id: dict[str, tuple[dict[str, Any], str]] = {}
    context = evidence_response.get("answer_context", {})
    if isinstance(context, dict):
        for collection, role in _EVIDENCE_ROLES:
            units = context.get(collection, [])
            if isinstance(units, list):
                for evidence in units:
                    if isinstance(evidence, dict) and "evidence_id" in evidence:
                        evidence_by_id.setdefault(evidence["evidence_id"], (evidence, role))

    for citation in citations:
        errors.extend(_validate_citation(citation, evidence_by_id))
    return {"valid": not errors, "errors": errors}


def _validate_citation(
    citation: Any, evidence_by_id: dict[str, tuple[dict[str, Any], str]]
) -> list[dict[str, str]]:
    if not isinstance(citation, dict):
        return [_error("INVALID_CITATION", "Each citation must be an object.")]
    evidence_id = citation.get("evidence_id")
    if not isinstance(evidence_id, str) or evidence_id not in evidence_by_id:
        return [
            _error(
                "UNKNOWN_EVIDENCE_ID",
                "Citation references evidence that was not retrieved.",
            )
        ]

    evidence = evidence_by_id[evidence_id][0]
    errors: list[dict[str, str]] = []
    for field in ("source_id", "filename"):
        if citation.get(field) != evidence.get(field):
            errors.append(
                _error(
                    f"WRONG_{field.upper()}",
                    f"Citation {field} does not match the cited evidence.",
                )
            )
    location = citation.get("location")
    if not isinstance(location, dict):
        return errors + [
            _error("INVALID_LOCATION", "Citation location must be an object.")
        ]
    for field in _LOCATION_FIELDS:
        if field in evidence and location.get(field) != evidence[field]:
            errors.append(
                _error(
                    "WRONG_LOCATION",
                    f"Citation location field '{field}' does not match the cited evidence.",
                )
            )
    return errors


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _result(code: str, message: str) -> dict[str, Any]:
    return {"valid": False, "errors": [_error(code, message)]}
