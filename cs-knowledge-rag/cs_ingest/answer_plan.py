"""Build deterministic, evidence-referenced plans for answer generation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_STATUSES = {"answerable", "insufficient_evidence", "clarification_required"}
_EVIDENCE_COLLECTIONS = (
    ("supporting_evidence", "supporting"),
    ("independent_evidence", "independent"),
)
_PROVENANCE_FIELDS = ("source_id", "filename", "page", "sheet", "row", "cell", "cell_range")


def build_answer_plan(evidence_response: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic plan without changing the supplied response."""
    if not isinstance(evidence_response, dict):
        raise ValueError("Evidence response must be an object.")

    status = evidence_response.get("status")
    if status not in _STATUSES:
        raise ValueError(f"Unsupported evidence response status: {status}")

    context = evidence_response.get("answer_context", {})
    if not isinstance(context, dict):
        raise ValueError("Evidence response answer_context must be an object.")

    if status != "answerable":
        return _empty_plan(status)

    evidence_by_id, roles = _selected_evidence(context)
    records = context.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Evidence response records must be a list.")

    metadata = _selection_metadata(evidence_response)
    grouped_evidence = _group_evidence_ids(metadata)
    observations, evidence_observation_ids = _observations(
        records, evidence_by_id, roles, grouped_evidence
    )
    conflict_groups = _groups(
        metadata, "conflict_groups", evidence_observation_ids, conflict=True
    )
    lifecycle_groups = _groups(
        metadata, "lifecycle_groups", evidence_observation_ids, lifecycle=True
    )
    for observation in observations:
        if grouped_evidence.intersection(observation["evidence_ids"]):
            observation["preserve_separately"] = True
            observation["reason"] = "member of a selector-derived group"

    coverage = _coverage(metadata, conflict_groups, lifecycle_groups)
    return {
        "schema_version": "1.0",
        "answerability": status,
        "observations": observations,
        "conflict_groups": conflict_groups,
        "lifecycle_groups": lifecycle_groups,
        "citation_requirements": {
            "claim_must_reference_selected_evidence": True,
            "allowed_evidence_ids": sorted(evidence_by_id),
            "supporting_evidence_ids": sorted(roles["supporting"]),
            "independent_evidence_ids": sorted(roles["independent"]),
        },
        "coverage": coverage,
        "unsupported_or_ambiguous": _unsupported_or_ambiguous(evidence_response, metadata),
    }


def _empty_plan(status: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "answerability": status,
        "observations": [],
        "conflict_groups": [],
        "lifecycle_groups": [],
        "citation_requirements": {
            "claim_must_reference_selected_evidence": False,
            "allowed_evidence_ids": [],
            "supporting_evidence_ids": [],
            "independent_evidence_ids": [],
        },
        "coverage": {
            "complete": False,
            "truncated": False,
            "conflict_coverage_complete": False,
            "missing_groups": [],
            "excluded_evidence_ids": [],
            "warnings": [],
        },
        "unsupported_or_ambiguous": [],
    }


def _selected_evidence(
    context: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    evidence_by_id: dict[str, dict[str, Any]] = {}
    role_ids = {"supporting": set(), "independent": set()}
    for collection, role in _EVIDENCE_COLLECTIONS:
        units = context.get(collection, [])
        if not isinstance(units, list):
            raise ValueError(f"Evidence response {collection} must be a list.")
        for unit in units:
            if not isinstance(unit, dict) or not isinstance(
                unit.get("evidence_id"), str
            ):
                raise ValueError("Selected evidence must contain an evidence_id.")
            evidence_id = unit["evidence_id"]
            existing = evidence_by_id.get(evidence_id)
            if existing is not None and existing != unit:
                raise ValueError(f"Conflicting evidence_id: {evidence_id}")
            evidence_by_id[evidence_id] = deepcopy(unit)
            role_ids[role].add(evidence_id)
    return evidence_by_id, role_ids


def _observations(
    records: list[Any],
    evidence_by_id: dict[str, dict[str, Any]],
    roles: dict[str, set[str]],
    grouped_evidence: set[str],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    observations: list[dict[str, Any]] = []
    evidence_observation_ids: dict[str, list[str]] = {}
    attached_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Selected records must be objects.")
        record_id = record.get("record_id")
        if not isinstance(record_id, str):
            raise ValueError("Selected records must contain a record_id.")
        evidence_ids = sorted(
            {
                ref.get("evidence_id")
                for ref in record.get("evidence_refs", [])
                if isinstance(ref, dict)
                and isinstance(ref.get("evidence_id"), str)
                and ref.get("evidence_id") in evidence_by_id
            }
        )
        if not evidence_ids:
            continue
        observation_evidence = [
            [evidence_id] if evidence_id in grouped_evidence else evidence_ids
            for evidence_id in evidence_ids
            if evidence_id in grouped_evidence
        ]
        if len(observation_evidence) < 1:
            observation_evidence = [evidence_ids]
        elif any(evidence_id not in grouped_evidence for evidence_id in evidence_ids):
            observation_evidence.append(
                [evidence_id for evidence_id in evidence_ids if evidence_id not in grouped_evidence]
            )
        for evidence_group in observation_evidence:
            suffix = (
                f":evidence:{evidence_group[0]}"
                if len(observation_evidence) > 1
                else ""
            )
            observation_id = f"record:{record_id}{suffix}"
            observation = {
                "observation_id": observation_id,
                "record_ids": [record_id],
                "evidence_ids": evidence_group,
                "roles": _roles(evidence_group, roles),
                "preserve_separately": False,
                "reason": "distinct selected record",
            }
            matched_fields = record.get("matched_fields")
            if isinstance(matched_fields, list):
                observation["matched_fields"] = sorted(
                    {item for item in matched_fields if isinstance(item, str)}
                )
            observation["provenance_refs"] = _provenance_refs(
                evidence_group, evidence_by_id
            )
            observations.append(observation)
            for evidence_id in evidence_group:
                attached_ids.add(evidence_id)
                evidence_observation_ids.setdefault(evidence_id, []).append(
                    observation_id
                )

    for evidence_id in sorted(set(evidence_by_id) - attached_ids):
        observation_id = f"evidence:{evidence_id}"
        observations.append(
            {
                "observation_id": observation_id,
                "record_ids": [],
                "evidence_ids": [evidence_id],
                "roles": _roles([evidence_id], roles),
                "preserve_separately": False,
                "reason": "selected evidence without a selected record",
                "provenance_refs": _provenance_refs(
                    [evidence_id], evidence_by_id
                ),
            }
        )
        evidence_observation_ids[evidence_id] = [observation_id]

    observations.sort(key=lambda item: item["observation_id"])
    return observations, evidence_observation_ids


def _roles(evidence_ids: list[str], roles: dict[str, set[str]]) -> dict[str, list[str]]:
    return {
        "supporting": sorted(set(evidence_ids) & roles["supporting"]),
        "independent": sorted(set(evidence_ids) & roles["independent"]),
    }


def _provenance_refs(
    evidence_ids: list[str], evidence_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    refs = []
    for evidence_id in evidence_ids:
        evidence = evidence_by_id[evidence_id]
        reference = {"evidence_id": evidence_id}
        for field in _PROVENANCE_FIELDS:
            if field in evidence:
                reference[field] = deepcopy(evidence[field])
        refs.append(reference)
    return refs


def _selection_metadata(evidence_response: dict[str, Any]) -> dict[str, Any]:
    selection = evidence_response.get("selection", {})
    if not isinstance(selection, dict):
        return {}
    nested = selection.get("coverage")
    if isinstance(nested, dict):
        return {**selection, "coverage": nested}
    return selection


def _groups(
    metadata: dict[str, Any],
    key: str,
    evidence_observation_ids: dict[str, list[str]],
    *,
    conflict: bool = False,
    lifecycle: bool = False,
) -> list[dict[str, Any]]:
    coverage = metadata.get("coverage", {})
    if not isinstance(coverage, dict):
        return []
    raw_groups = coverage.get(key, [])
    if not raw_groups and key == "lifecycle_groups":
        raw_groups = [
            group
            for group in coverage.get("coverage_groups", [])
            if isinstance(group, dict) and group.get("kind") == "lifecycle"
        ]
    if not isinstance(raw_groups, list):
        return []
    result = []
    for raw in raw_groups:
        if not isinstance(raw, dict) or not isinstance(raw.get("coverage_group_id"), str):
            continue
        evidence_ids = sorted(
            item for item in raw.get("evidence_ids", []) if isinstance(item, str)
        )
        observation_ids = sorted(
            {
                observation_id
                for evidence_id in evidence_ids
                for observation_id in evidence_observation_ids.get(evidence_id, [])
            }
        )
        complete = raw.get("complete")
        if not isinstance(complete, bool):
            complete = not bool(raw.get("excluded_evidence_ids"))
        group = {
            "group_id": raw["coverage_group_id"],
            "observation_ids": observation_ids,
            "evidence_ids": evidence_ids,
            "complete": complete,
            "reason": raw.get("reason", ""),
        }
        if conflict:
            group["must_preserve_separately"] = True
        if lifecycle:
            group["must_distinguish"] = True
        group["selected_evidence_ids"] = sorted(
            item
            for item in raw.get("selected_evidence_ids", [])
            if isinstance(item, str)
        )
        group["excluded_evidence_ids"] = sorted(
            item
            for item in raw.get("excluded_evidence_ids", [])
            if isinstance(item, str)
        )
        result.append(group)
    return sorted(result, key=lambda item: item["group_id"])


def _group_evidence_ids(metadata: dict[str, Any]) -> set[str]:
    coverage = metadata.get("coverage", {})
    if not isinstance(coverage, dict):
        return set()
    groups = []
    for key in ("conflict_groups", "lifecycle_groups"):
        value = coverage.get(key, [])
        if isinstance(value, list):
            groups.extend(value)
    for group in coverage.get("coverage_groups", []):
        if isinstance(group, dict) and group.get("kind") == "lifecycle":
            groups.append(group)
    return {
        evidence_id
        for group in groups
        if isinstance(group, dict)
        for evidence_id in group.get("evidence_ids", [])
        if isinstance(evidence_id, str)
    }


def _coverage(
    metadata: dict[str, Any],
    conflict_groups: list[dict[str, Any]],
    lifecycle_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    raw = metadata.get("coverage", {})
    if not isinstance(raw, dict):
        raw = {}
    missing_groups = [
        deepcopy(group)
        for group in conflict_groups + lifecycle_groups
        if not group["complete"]
    ]
    excluded = raw.get("excluded_evidence_ids", metadata.get("excluded_evidence_ids", []))
    warnings = metadata.get("warnings", [])
    return {
        "complete": raw.get("coverage_complete", False)
        if isinstance(raw.get("coverage_complete", False), bool)
        else False,
        "truncated": bool(metadata.get("truncated", False)),
        "conflict_coverage_complete": raw.get(
            "conflict_coverage_complete", all(group["complete"] for group in conflict_groups)
        ),
        "missing_groups": missing_groups,
        "excluded_evidence_ids": sorted(
            item for item in excluded if isinstance(item, str)
        )
        if isinstance(excluded, list)
        else [],
        "warnings": sorted(item for item in warnings if isinstance(item, str))
        if isinstance(warnings, list)
        else [],
    }


def _unsupported_or_ambiguous(
    evidence_response: dict[str, Any], metadata: dict[str, Any]
) -> list[Any]:
    values = []
    for source in (evidence_response, metadata):
        value = source.get("unsupported_or_ambiguous")
        if isinstance(value, list):
            values.extend(deepcopy(value))
        elif isinstance(value, str):
            values.append(value)
    query_understanding = evidence_response.get("query_understanding", {})
    if isinstance(query_understanding, dict):
        unresolved = query_understanding.get("unresolved")
        if unresolved:
            values.append(deepcopy(unresolved))
    return values
