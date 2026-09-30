"""Deterministic evaluation of claim-level answer obligations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def evaluate_obligations(
    question: str,
    obligation: dict[str, Any],
    internal_output: dict[str, Any],
    citation_handle_mapping: dict[str, Any],
    selected_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate one answer against explicit, structured obligations."""
    if question != obligation.get("question"):
        raise ValueError("Question does not match obligation.")
    claims = internal_output.get("claims", [])
    evidence_by_id = {
        evidence["evidence_id"]: evidence
        for evidence in selected_evidence
        if isinstance(evidence, dict) and evidence.get("evidence_id")
    }
    handle_ids = {
        handle: _evidence_id(value)
        for handle, value in citation_handle_mapping.items()
    }
    invalid_refs = sorted(
        ref
        for claim in claims
        for ref in claim.get("citation_refs", [])
        if ref not in handle_ids
    )
    required = []
    satisfied = []
    missing = []
    wrong = []
    for item in obligation.get("required_observations", []):
        required.append(item["id"])
        match = _find_claim(item, claims, handle_ids, evidence_by_id)
        if match is None:
            missing.append(item["id"])
        elif match["wrong_citation"]:
            wrong.append(item["id"])
        else:
            satisfied.append(item["id"])

    conflict_results = _evaluate_groups(
        obligation.get("conflict_requirements", []),
        claims,
        handle_ids,
        evidence_by_id,
    )
    lifecycle_results = _evaluate_groups(
        obligation.get("lifecycle_requirements", []),
        claims,
        handle_ids,
        evidence_by_id,
    )
    for group in conflict_results + lifecycle_results:
        if not group["complete"]:
            missing.append(group["id"])

    direct_results = _evaluate_direct_requirements(
        obligation.get("direct_citation_requirements", []),
        claims,
        handle_ids,
        evidence_by_id,
    )
    for item in direct_results:
        if item["wrong_citation"]:
            wrong.append(item["id"])

    has_supported_content = bool(satisfied or any(
        group["satisfied"] for group in conflict_results + lifecycle_results
    ))
    if invalid_refs or (not has_supported_content and missing):
        status = "FAIL"
    elif missing or wrong:
        status = "PARTIAL"
    else:
        status = "PASS"
    return {
        "status": status,
        "required_obligations": required,
        "satisfied_obligations": sorted(set(satisfied)),
        "missing_obligations": sorted(set(missing)),
        "wrong_citation_obligations": sorted(set(wrong)),
        "invalid_evidence_handles": invalid_refs,
        "conflict_preservation": conflict_results,
        "lifecycle_distinction": lifecycle_results,
        "direct_citation_requirements": direct_results,
        "acceptable_scope": deepcopy(obligation.get("acceptable_scope", [])),
        "incomplete_conditions": deepcopy(obligation.get("incomplete_conditions", [])),
    }


def _find_claim(
    requirement: dict[str, Any],
    claims: list[dict[str, Any]],
    handle_ids: dict[str, str],
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for claim in claims:
        text = str(claim.get("text", "")).casefold()
        if not _matches_phrases(requirement, text):
            continue
        cited = {
            handle_ids[ref]
            for ref in claim.get("citation_refs", [])
            if ref in handle_ids
        }
        required_evidence = requirement.get("required_evidence", [])
        complete = all(
            any(_matches_selector(selector, evidence_by_id.get(evidence_id, {}))
                for evidence_id in cited)
            for selector in required_evidence
        )
        return {"claim": claim, "wrong_citation": not complete}
    return None


def _evaluate_groups(groups, claims, handle_ids, evidence_by_id):
    results = []
    for group in groups:
        observations = []
        for observation in group.get("observations", []):
            match = _find_claim(observation, claims, handle_ids, evidence_by_id)
            observations.append({
                "id": observation["id"],
                "satisfied": match is not None and not match["wrong_citation"],
                "wrong_citation": bool(match and match["wrong_citation"]),
            })
        results.append({
            "id": group["id"],
            "satisfied": all(item["satisfied"] for item in observations),
            "complete": all(item["satisfied"] for item in observations),
            "observations": observations,
        })
    return results


def _evaluate_direct_requirements(requirements, claims, handle_ids, evidence_by_id):
    results = []
    for requirement in requirements:
        match = _find_claim(requirement, claims, handle_ids, evidence_by_id)
        results.append({
            "id": requirement["observation_id"],
            "satisfied": bool(match and not match["wrong_citation"]),
            "wrong_citation": bool(match and match["wrong_citation"]),
        })
    return results


def _matches_phrases(requirement: dict[str, Any], text: str) -> bool:
    return all(phrase.casefold() in text for phrase in requirement.get("all_phrases", [])) and (
        not requirement.get("any_phrases")
        or any(phrase.casefold() in text for phrase in requirement["any_phrases"])
    )


def _matches_selector(selector: dict[str, Any], evidence: dict[str, Any]) -> bool:
    return all(
        _nested_value(evidence, key) == value
        for key, value in selector.items()
        if key != "location"
    ) and all(
        _nested_value(evidence, key) == value
        for key, value in selector.get("location", {}).items()
    )


def _nested_value(evidence: dict[str, Any], key: str) -> Any:
    return evidence.get(key)


def _evidence_id(value: Any) -> str:
    return value if isinstance(value, str) else value.get("evidence_id", "")
