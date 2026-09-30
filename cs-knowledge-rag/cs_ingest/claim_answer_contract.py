"""Validation for the internal claim-based model answer contract."""

from __future__ import annotations

from typing import Any

from .citation_builder import citation_handles

_STATUSES = {"answered", "insufficient_evidence", "clarification_required"}
_CLAIM_FIELDS = {"text", "citation_refs"}
_RAW_PROVENANCE_FIELDS = {
    "evidence_id",
    "source_id",
    "filename",
    "page",
    "row",
    "cell",
    "cell_range",
    "location",
}


class ClaimAnswerContractError(ValueError):
    """The model output does not satisfy the internal claim contract."""


def validate_claim_answer(
    model_output: dict[str, Any],
    selected_evidence_response: dict[str, Any],
) -> dict[str, Any]:
    """Validate claims and exact citation handles before citation building."""
    if not isinstance(model_output, dict):
        raise ClaimAnswerContractError("Model output must be an object.")
    if set(model_output) != {"status", "claims"}:
        raise ClaimAnswerContractError("Model output must contain only status and claims.")
    status = model_output.get("status")
    claims = model_output.get("claims")
    if status not in _STATUSES:
        raise ClaimAnswerContractError("Model output status is unsupported.")
    if not isinstance(claims, list):
        raise ClaimAnswerContractError("claims must be a list.")
    if status != "answered":
        if claims:
            raise ClaimAnswerContractError(
                f"{status} responses must contain empty claims."
            )
        return {"valid": True, "errors": []}
    if not claims:
        raise ClaimAnswerContractError("Answered responses require claims.")

    handles = citation_handles(selected_evidence_response)
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != _CLAIM_FIELDS:
            raise ClaimAnswerContractError(
                "Each claim must contain only text and citation_refs."
            )
        if _contains_raw_provenance(claim):
            raise ClaimAnswerContractError(
                "Claims must not contain raw provenance fields."
            )
        text = claim["text"]
        refs = claim["citation_refs"]
        if not isinstance(text, str) or not text.strip():
            raise ClaimAnswerContractError("Each claim requires non-empty text.")
        if not isinstance(refs, list) or not refs:
            raise ClaimAnswerContractError(
                "Each claim requires at least one citation ref."
            )
        if any(not isinstance(ref, str) or ref not in handles for ref in refs):
            raise ClaimAnswerContractError(
                "Each citation ref must exactly match supplied evidence handles."
            )
        if len(refs) != len(set(refs)):
            raise ClaimAnswerContractError(
                "Duplicate citation refs are not allowed within a claim."
            )
    return {"valid": True, "errors": []}


def _contains_raw_provenance(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in _RAW_PROVENANCE_FIELDS or _contains_raw_provenance(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_raw_provenance(item) for item in value)
    return False
