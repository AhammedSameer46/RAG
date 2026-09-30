"""Deterministic internal claim generation from an evidence response."""

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
            return {"status": status, "claims": []}
        if status == "clarification_required":
            return {"status": status, "claims": []}
        if status != "answerable":
            raise ValueError(f"Unsupported evidence response status: {status}")

        context = evidence_response["answer_context"]
        supporting = _deduplicate(context.get("supporting_evidence", []))
        independent = _deduplicate(context.get("independent_evidence", []))
        records = context.get("records", [])

        cited_ids = {evidence["evidence_id"] for evidence in supporting}
        independent_only = [
            evidence
            for evidence in independent
            if evidence["evidence_id"] not in cited_ids
        ]
        selected = supporting + independent_only

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
            "claims": [
                {
                    "text": "\n".join(lines),
                    "citation_refs": [f"E{index}" for index in range(1, len(selected) + 1)],
                }
            ],
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

