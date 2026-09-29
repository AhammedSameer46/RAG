"""Build provenance-preserving evidence packages from pipeline results."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_STATUSES = {"answerable", "insufficient_evidence", "clarification_required"}


def build_evidence_response(pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """Organize a pipeline result without answering or summarizing it."""
    status = pipeline_result["status"]
    if status not in _STATUSES:
        raise ValueError(f"Unsupported pipeline status: {status}")

    retrieval = pipeline_result["retrieval"]
    include_context = status == "answerable"
    supporting = (
        _deduplicate_evidence(retrieval.get("supporting_evidence_units", []))
        if include_context
        else []
    )
    independent = (
        _deduplicate_evidence(retrieval.get("matched_evidence_units", []))
        if include_context
        else []
    )
    records = deepcopy(retrieval.get("records", [])) if include_context else []
    sources = _build_sources(supporting + independent)

    return {
        "question": pipeline_result["question"],
        "status": status,
        "query_understanding": deepcopy(
            pipeline_result.get("query_understanding", {})
        ),
        "answer_context": {
            "records": records,
            "supporting_evidence": supporting,
            "independent_evidence": independent,
        },
        "sources": sources,
        "coverage": {
            "has_records": bool(records),
            "has_supporting_evidence": bool(supporting),
            "has_independent_evidence": bool(independent),
        },
    }


def _deduplicate_evidence(evidence_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for evidence in evidence_units:
        evidence_id = evidence["evidence_id"]
        if evidence_id not in unique:
            unique[evidence_id] = deepcopy(evidence)
    return [unique[evidence_id] for evidence_id in sorted(unique)]


def _build_sources(evidence_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for evidence in evidence_units:
        source_id = evidence["source_id"]
        source = grouped.setdefault(
            source_id,
            {"source_id": source_id, "filename": evidence["filename"], "evidence_ids": []},
        )
        if evidence["evidence_id"] not in source["evidence_ids"]:
            source["evidence_ids"].append(evidence["evidence_id"])
    return [
        {
            **grouped[source_id],
            "evidence_ids": sorted(grouped[source_id]["evidence_ids"]),
        }
        for source_id in sorted(grouped)
    ]
