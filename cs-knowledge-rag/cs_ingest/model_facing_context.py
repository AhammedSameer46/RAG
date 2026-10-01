"""Build a compact, provider-neutral context for answer generation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .citation_builder import citation_handles

_EVIDENCE_COLLECTIONS = ("supporting_evidence", "independent_evidence")
_LOCATION_FIELDS = ("page", "sheet", "row", "cell", "cell_range")
_FORBIDDEN_KEYS = {
    "source_id",
    "evidence_id",
    "record_id",
    "provenance_refs",
    "matched_fields",
    "selector_scores",
    "evaluator",
    "expected_answer",
    "password",
    "token",
    "secret",
    "authorization",
    "authentication",
}


def build_model_facing_context(
    evidence_response: dict[str, Any],
) -> dict[str, Any]:
    """Build compact model-facing data without mutating the response."""
    if not isinstance(evidence_response, dict):
        raise ValueError("Evidence response must be an object.")
    plan = evidence_response.get("answer_plan")
    if not isinstance(plan, dict):
        raise ValueError("Evidence response answer_plan must be an object.")
    context = evidence_response.get("answer_context")
    if not isinstance(context, dict):
        raise ValueError("Evidence response answer_context must be an object.")

    handles = citation_handles(evidence_response)
    evidence_by_id = {
        evidence["evidence_id"]: evidence for evidence in handles.values()
    }
    handle_by_id = {
        evidence["evidence_id"]: handle
        for handle, evidence in handles.items()
    }
    roles = _roles(context, handles)
    evidence = [
        _compact_evidence(handle, item, roles)
        for handle, item in handles.items()
    ]
    observations = _compact_observations(plan, handle_by_id, evidence_by_id)
    observation_indexes = {
        _observation_key(observation): index
        for index, observation in enumerate(plan.get("observations", []))
    }
    compact_plan = {
        "observations": observations,
        "conflict_groups": _compact_groups(
            plan, "conflict_groups", observation_indexes, "must_preserve_separately"
        ),
        "lifecycle_groups": _compact_groups(
            plan, "lifecycle_groups", observation_indexes, "must_distinguish"
        ),
        "coverage": _compact_coverage(plan),
    }
    result = {"answer_plan": compact_plan, "evidence": evidence}
    _validate_result(result)
    return result


def _roles(
    context: dict[str, Any], handles: dict[str, dict[str, Any]]
) -> dict[str, str]:
    roles: dict[str, str] = {}
    for collection, role in (
        ("supporting_evidence", "supporting"),
        ("independent_evidence", "independent"),
    ):
        units = context.get(collection, [])
        if not isinstance(units, list):
            raise ValueError(f"Evidence response {collection} must be a list.")
        for unit in units:
            if not isinstance(unit, dict):
                raise ValueError("Selected evidence must be an object.")
            evidence_id = unit.get("evidence_id")
            if evidence_id not in {
                evidence.get("evidence_id") for evidence in handles.values()
            }:
                raise ValueError("Selected evidence handle mapping is inconsistent.")
            existing = roles.get(evidence_id)
            if existing is None or existing == "independent":
                roles[evidence_id] = role
    return roles


def _compact_evidence(
    handle: str, evidence: dict[str, Any], roles: dict[str, str]
) -> dict[str, Any]:
    filename = evidence.get("filename")
    if not isinstance(filename, str) or not filename:
        raise ValueError(f"Evidence {handle} requires a filename.")
    text = evidence.get("extracted_text")
    raw_values = evidence.get("raw_values")
    if not isinstance(text, str) or not text.strip():
        text = _render_raw_values(evidence)
    if not text.strip():
        raise ValueError(f"Evidence {handle} requires non-empty text.")

    compact: dict[str, Any] = {
        "id": handle,
        "source": filename,
        "location": {
            key: deepcopy(evidence[key])
            for key in _LOCATION_FIELDS
            if key in evidence and evidence[key] is not None
        },
        "text": text,
    }
    if _include_role(roles):
        compact["role"] = roles[evidence["evidence_id"]]
    if _needs_raw_values(evidence, text):
        compact["raw_values"] = deepcopy(raw_values)
    return compact


def _include_role(roles: dict[str, str]) -> bool:
    return len(set(roles.values())) > 1


def _needs_raw_values(evidence: dict[str, Any], text: str) -> bool:
    raw_values = evidence.get("raw_values")
    return bool(raw_values) and not evidence.get("extracted_text", "").strip()


def _render_raw_values(evidence: dict[str, Any]) -> str:
    raw_values = evidence.get("raw_values")
    if not raw_values:
        return ""
    headers = evidence.get("header_context")
    if isinstance(raw_values, dict):
        if isinstance(headers, dict):
            return " | ".join(
                f"{headers.get(key, key)}: {value}"
                for key, value in raw_values.items()
            )
        return " | ".join(f"{key}: {value}" for key, value in raw_values.items())
    if isinstance(raw_values, list):
        return " | ".join(str(value) for value in raw_values)
    return str(raw_values)


def _compact_observations(
    plan: dict[str, Any],
    handle_by_id: dict[str, str],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    source = plan.get("observations")
    if not isinstance(source, list):
        raise ValueError("Answer Plan observations must be a list.")
    compact = []
    for observation in source:
        if not isinstance(observation, dict):
            raise ValueError("Answer Plan observation must be an object.")
        evidence_ids = observation.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError("Answer Plan observation requires evidence_ids.")
        handles = []
        for evidence_id in evidence_ids:
            if evidence_id not in evidence_by_id:
                raise ValueError(
                    f"Observation references unknown evidence: {evidence_id}"
                )
            handles.append(handle_by_id[evidence_id])
        compact.append(
            {
                "evidence_ids": handles,
                "preserve_separately": _required_bool(
                    observation, "preserve_separately"
                ),
            }
        )
    return compact


def _observation_key(observation: dict[str, Any]) -> str:
    observation_id = observation.get("observation_id")
    if not isinstance(observation_id, str) or not observation_id:
        raise ValueError("Answer Plan observation requires observation_id.")
    return observation_id


def _compact_groups(
    plan: dict[str, Any],
    field: str,
    observation_indexes: dict[str, int],
    flag: str,
) -> list[dict[str, Any]]:
    groups = plan.get(field)
    if not isinstance(groups, list):
        raise ValueError(f"Answer Plan {field} must be a list.")
    compact = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError(f"Answer Plan {field} member must be an object.")
        ids = group.get("observation_ids")
        if not isinstance(ids, list):
            raise ValueError(f"Answer Plan {field} member requires observation_ids.")
        if not ids:
            continue
        indexes = []
        for observation_id in ids:
            if observation_id not in observation_indexes:
                raise ValueError(
                    f"{field} references unknown observation: {observation_id}"
                )
            indexes.append(observation_indexes[observation_id])
        compact.append(
            {
                "observation_indexes": indexes,
                flag: _required_bool(group, flag),
            }
        )
    return compact


def _compact_coverage(plan: dict[str, Any]) -> dict[str, Any]:
    coverage = plan.get("coverage")
    if not isinstance(coverage, dict) or not isinstance(
        coverage.get("complete"), bool
    ):
        raise ValueError("Answer Plan coverage.complete must be a boolean.")
    compact = {"complete": coverage["complete"]}
    if not coverage["complete"]:
        compact["reason"] = (
            "selection_budget"
            if coverage.get("truncated")
            or coverage.get("excluded_evidence_ids")
            else "incomplete"
        )
    return compact


def _required_bool(value: dict[str, Any], field: str) -> bool:
    if not isinstance(value.get(field), bool):
        raise ValueError(f"Answer Plan field {field} must be a boolean.")
    return value[field]


def _validate_result(result: dict[str, Any]) -> None:
    plan = result["answer_plan"]
    evidence = result["evidence"]
    handles = [item["id"] for item in evidence]
    if len(handles) != len(set(handles)):
        raise ValueError("Model-facing evidence handles must be unique.")
    evidence_set = set(handles)
    observations = plan["observations"]
    for observation in observations:
        if not set(observation["evidence_ids"]) <= evidence_set:
            raise ValueError("Observation references an unknown evidence handle.")
    for field in ("conflict_groups", "lifecycle_groups"):
        for group in plan[field]:
            for index in group["observation_indexes"]:
                if not isinstance(index, int) or not 0 <= index < len(observations):
                    raise ValueError(f"{field} contains an invalid observation index.")
            if len(group["observation_indexes"]) != len(
                set(group["observation_indexes"])
            ):
                raise ValueError(f"{field} contains duplicate observation indexes.")
    _validate_no_forbidden_keys(result)


def _validate_no_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        leaked = _FORBIDDEN_KEYS.intersection(value)
        if leaked:
            raise ValueError(
                "Model-facing context contains forbidden internal fields: "
                + ", ".join(sorted(leaked))
            )
        for item in value.values():
            _validate_no_forbidden_keys(item)
    elif isinstance(value, list):
        for item in value:
            _validate_no_forbidden_keys(item)
