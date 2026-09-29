"""Deterministic answer-contract generation from an evidence response."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class MockAnswerGenerator:
    """Create a literal, evidence-referencing answer without inference."""

    def generate(
        self,
        question: str | dict[str, Any],
        evidence_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if evidence_response is None:
            evidence_response = question
        if not isinstance(evidence_response, dict):
            raise TypeError("evidence_response must be a dictionary")
        status = evidence_response["status"]
        if status == "insufficient_evidence":
            return {"status": status, "answer": "", "citations": []}
        if status == "clarification_required":
            return {"status": status, "answer": "", "citations": []}
        if status != "answerable":
            raise ValueError(f"Unsupported evidence response status: {status}")

        context = evidence_response["answer_context"]
        supporting = _deduplicate(context.get("supporting_evidence", []))
        independent = _deduplicate(context.get("independent_evidence", []))
        records = context.get("records", [])

        citations = [_citation(evidence) for evidence in supporting]
        cited_ids = {citation["evidence_id"] for citation in citations}
        independent_only = [
            evidence
            for evidence in independent
            if evidence["evidence_id"] not in cited_ids
        ]
        citations.extend(_citation(evidence) for evidence in independent_only)

        lines = [
            "Retrieved records: "
            + (", ".join(record["record_id"] for record in records) or "none")
        ]
        if independent_only:
            lines.append(
                "Independently matched evidence: "
                + ", ".join(evidence["evidence_id"] for evidence in independent_only)
            )
        return {
            "status": "answered",
            "answer": "\n".join(lines),
            "citations": citations,
        }


def generate_mock_answer(
    question: str | dict[str, Any],
    evidence_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate one deterministic answer-contract object."""
    return MockAnswerGenerator().generate(question, evidence_response)


def _deduplicate(evidence_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for evidence in evidence_units:
        unique.setdefault(evidence["evidence_id"], deepcopy(evidence))
    return [unique[evidence_id] for evidence_id in sorted(unique)]


def _citation(evidence: dict[str, Any]) -> dict[str, Any]:
    location = {
        field: evidence[field]
        for field in ("page", "sheet", "row", "cell", "cell_range")
        if field in evidence
    }
    return {
        "evidence_id": evidence["evidence_id"],
        "source_id": evidence["source_id"],
        "filename": evidence["filename"],
        "location": location,
    }
