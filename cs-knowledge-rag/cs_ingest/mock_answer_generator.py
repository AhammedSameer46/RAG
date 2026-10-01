"""Deterministic internal claim generation from compact model context."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class MockAnswerGenerator:
    """Create a literal, evidence-referencing answer without inference."""

    def generate(
        self,
        question: str | dict[str, Any],
        model_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if model_context is None and isinstance(question, dict):
            return _generate_legacy(question)
        if model_context is None or not isinstance(model_context, dict):
            raise TypeError("model_context must be a dictionary")
        evidence = model_context.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError("model_context evidence must be a list")
        return {
            "status": "answered",
            "claims": [
                {
                    "text": "Retrieved evidence was supplied.",
                    "citation_refs": [
                        item["id"] for item in evidence if isinstance(item, dict)
                    ],
                }
            ],
        }


def generate_mock_answer(
    question: str | dict[str, Any],
    model_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate one deterministic evidence-referencing answer."""
    return MockAnswerGenerator().generate(question, model_context)


def _generate_legacy(evidence_response: dict[str, Any]) -> dict[str, Any]:
    context = evidence_response["answer_context"]
    supporting = _deduplicate(context.get("supporting_evidence", []))
    independent = _deduplicate(context.get("independent_evidence", []))
    supporting_ids = {evidence["evidence_id"] for evidence in supporting}
    independent_only = [
        evidence
        for evidence in independent
        if evidence["evidence_id"] not in supporting_ids
    ]
    selected = supporting + independent_only
    lines = [
        "Retrieved records: "
        + (", ".join(record["record_id"] for record in context.get("records", [])) or "none")
    ]
    if independent_only:
        lines.append(
            "Independently matched evidence: "
            + ", ".join(evidence["evidence_id"] for evidence in independent_only)
        )
    return {
        "status": "answered",
        "claims": [{
            "text": "\n".join(lines),
            "citation_refs": [f"E{index}" for index in range(1, len(selected) + 1)],
        }],
    }


def _deduplicate(evidence_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for evidence in evidence_units:
        unique.setdefault(evidence["evidence_id"], deepcopy(evidence))
    return [unique[evidence_id] for evidence_id in sorted(unique)]
