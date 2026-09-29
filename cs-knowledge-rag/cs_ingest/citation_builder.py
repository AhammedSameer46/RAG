"""Deterministic conversion from model citation handles to final citations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_EVIDENCE_COLLECTIONS = ("supporting_evidence", "independent_evidence")
_PROVENANCE_FIELDS = ("page", "sheet", "row", "cell", "cell_range")
_STATUSES = {"answered", "insufficient_evidence", "clarification_required"}


class CitationBuilderError(ValueError):
    """The model returned an invalid citation reference contract."""


class CitationBuilder:
    """Map short model handles to exact provenance in selected evidence."""

    def build(
        self,
        model_output: dict[str, Any],
        selected_evidence_response: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(model_output, dict):
            raise CitationBuilderError("Model output must be an object.")
        if set(model_output) != {"status", "answer", "citation_refs"}:
            raise CitationBuilderError("Model output has unexpected fields.")
        status = model_output.get("status")
        if status not in _STATUSES:
            raise CitationBuilderError("Model output status is unsupported.")
        answer = model_output.get("answer")
        refs = model_output.get("citation_refs")
        if not isinstance(answer, str):
            raise CitationBuilderError("Model output answer must be text.")
        if not isinstance(refs, list) or any(
            not isinstance(ref, str) for ref in refs
        ):
            raise CitationBuilderError("citation_refs must be a list of strings.")
        if len(refs) != len(set(refs)):
            raise CitationBuilderError("Duplicate citation refs are not allowed.")

        if status in {"insufficient_evidence", "clarification_required"}:
            if answer.strip() or refs:
                raise CitationBuilderError(
                    f"{status} responses require an empty answer and citations."
                )
            return {"status": status, "answer": "", "citations": []}

        if not answer.strip():
            raise CitationBuilderError("Answered responses require answer text.")
        if not refs:
            raise CitationBuilderError(
                "Answered responses require at least one citation ref."
            )

        handles = _handle_map(selected_evidence_response)
        citations = []
        for ref in refs:
            evidence = handles.get(ref)
            if evidence is None:
                raise CitationBuilderError(
                    f"Unknown citation ref: {ref}"
                )
            citation = {
                "evidence_id": evidence["evidence_id"],
                "source_id": evidence["source_id"],
                "filename": evidence["filename"],
                "location": {
                    field: deepcopy(evidence[field])
                    for field in _PROVENANCE_FIELDS
                    if field in evidence
                },
            }
            citations.append(citation)
        return {"status": status, "answer": answer, "citations": citations}


def citation_handles(
    selected_evidence_response: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return the stable E1, E2, ... mapping for selected evidence."""
    return _handle_map(selected_evidence_response)


def _handle_map(
    selected_evidence_response: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    try:
        context = selected_evidence_response["answer_context"]
    except (KeyError, TypeError) as exc:
        raise CitationBuilderError("Selected evidence context is missing.") from exc
    if not isinstance(context, dict):
        raise CitationBuilderError("Selected evidence context must be an object.")

    handles = {}
    seen_ids = set()
    index = 1
    for collection in _EVIDENCE_COLLECTIONS:
        units = context.get(collection, [])
        if not isinstance(units, list):
            raise CitationBuilderError(f"{collection} must be a list.")
        for evidence in units:
            if not isinstance(evidence, dict) or not isinstance(
                evidence.get("evidence_id"), str
            ):
                raise CitationBuilderError("Selected evidence is malformed.")
            evidence_id = evidence["evidence_id"]
            if evidence_id in seen_ids:
                continue
            handles[f"E{index}"] = evidence
            seen_ids.add(evidence_id)
            index += 1
    return handles
