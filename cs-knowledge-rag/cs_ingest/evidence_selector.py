"""Deterministic, provenance-preserving evidence selection."""

from __future__ import annotations

import json
import re
import hashlib
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceSelectionConfig:
    max_evidence_units: int = 6
    max_characters: int = 12000
    max_records: int = 8
    max_characters_per_unit: int | None = None


class EvidenceSelector:
    """Select bounded evidence without changing its meaning or provenance."""

    def select(
        self,
        question: str,
        query_understanding: dict[str, Any],
        evidence_response: dict[str, Any],
        config: EvidenceSelectionConfig,
    ) -> dict[str, Any]:
        status = evidence_response.get("status")
        context = evidence_response.get("answer_context", {})
        if not isinstance(context, dict):
            raise ValueError("evidence_response.answer_context must be an object")
        records = context.get("records", [])
        supporting = _deduplicate_units(context.get("supporting_evidence", []))
        independent = _deduplicate_units(context.get("independent_evidence", []))
        _validate_cross_role_duplicates(supporting, independent)
        if status != "answerable":
            return _empty_result(
                status, config, len(records), len(supporting) + len(independent)
            )

        units_by_id: dict[str, tuple[dict[str, Any], str]] = {}
        for unit in supporting:
            units_by_id[unit["evidence_id"]] = (unit, "supporting")
        for unit in independent:
            units_by_id.setdefault(unit["evidence_id"], (unit, "independent"))
        all_units = list(units_by_id.values())

        record_by_evidence = {
            ref["evidence_id"]: record
            for record in records
            for ref in record.get("evidence_refs", [])
            if isinstance(ref, dict) and "evidence_id" in ref
        }
        filters = query_understanding.get("filters", {})
        keywords = _tokens(question, filters.get("keyword", ""))
        date = filters.get("date")
        record_type = filters.get("record_type")
        person = filters.get("person")
        event_name = filters.get("event_name")
        date_role = filters.get("date_role")
        conflicts = _detect_conflicts(records)
        conflict_ids = {eid for conflict in conflicts for eid in conflict["evidence_ids"]}
        coverage_groups = _derive_coverage_groups(
            records, all_units, record_by_evidence, filters, query_understanding
        )
        grouped_ids = {
            evidence_id
            for group in coverage_groups
            for evidence_id in group["evidence_ids"]
        }
        primary_ids = _primary_date_activity_ids(
            all_units, record_by_evidence, query_understanding, date
        )
        if primary_ids:
            coverage_groups.append(
                {
                    "coverage_group_id": _stable_group_id(
                        "date_activity_primary", sorted(primary_ids)
                    ),
                    "kind": "primary_record_types",
                    "evidence_ids": sorted(primary_ids),
                    "reason": "distinct directly relevant record types.",
                }
            )

        ranked = []
        for unit, role in all_units:
            evidence_id = unit["evidence_id"]
            record = record_by_evidence.get(evidence_id)
            score = 0
            reasons: list[str] = []
            if role == "supporting":
                score += 100
                reasons.append("supporting")
            if record:
                score += 100
                reasons.append("record_support")
                attrs = record.get("attributes", {})
                if date and date in _record_dates(record):
                    score += 50
                    reasons.append("date")
                if record_type and record.get("record_type") == record_type:
                    score += 30
                    reasons.append("record_type")
                if person and person == attrs.get("person"):
                    score += 30
                    reasons.append("person")
                if event_name and event_name == attrs.get("name"):
                    score += 30
                    reasons.append("event_name")
                if date_role and _date_role_matches(record, date_role):
                    score += 20
                    reasons.append("date_role")
            overlap = sum(token in _flatten(unit).casefold() for token in keywords)
            if overlap:
                score += overlap * 10
                reasons.append("keyword")
            if evidence_id in grouped_ids:
                score += 90
                reasons.append("conflict_protected")
            if evidence_id in primary_ids:
                score += 80
                reasons.append("primary_coverage")
            score += _specificity(unit)
            if evidence_id in grouped_ids or evidence_id in primary_ids:
                priority_tier = 0
            elif role == "supporting":
                priority_tier = 0
            elif record:
                priority_tier = 2
            else:
                priority_tier = 3
            ranked.append(
                (priority_tier, -score, evidence_id, unit, role, reasons, record)
            )
        ranked.sort(key=lambda item: item[:3])

        selected: list[tuple[dict[str, Any], str, list[str], dict[str, Any] | None]] = []
        selected_records: list[dict[str, Any]] = []
        selected_record_ids: set[str] = set()
        excluded: list[dict[str, Any]] = []
        chars = 0
        for _, _, evidence_id, unit, role, reasons, record in ranked:
            unit_chars = _serialized_length(unit)
            if (
                config.max_characters_per_unit is not None
                and unit_chars > config.max_characters_per_unit
            ):
                excluded.append(
                    _exclusion(evidence_id, role, reasons, "max_characters_per_unit")
                )
                continue
            if len(selected) >= config.max_evidence_units:
                excluded.append(_exclusion(evidence_id, role, reasons, "budget_exceeded"))
                continue

            new_record = record is not None and record["record_id"] not in selected_record_ids
            if new_record and len(selected_records) >= config.max_records:
                excluded.append(_exclusion(evidence_id, role, reasons, "max_records"))
                continue

            candidate_records = selected_records + ([record] if new_record else [])
            candidate_units = selected + [(unit, role, reasons, record)]
            candidate_context = _context(
                candidate_records,
                candidate_units,
            )
            candidate_chars = _serialized_length(candidate_context)
            if candidate_chars > config.max_characters:
                excluded.append(
                    _exclusion(evidence_id, role, reasons, "max_characters")
                )
                continue

            selected.append((unit, role, reasons, record))
            chars = candidate_chars
            if new_record:
                selected_records.append(record)
                selected_record_ids.add(record["record_id"])

        selected_supporting = [
            deepcopy(unit) for unit, role, _, _ in selected if role == "supporting"
        ]
        selected_independent = [
            deepcopy(unit) for unit, role, _, _ in selected if role == "independent"
        ]
        selected_records_copy = deepcopy(selected_records)
        excluded_ids = sorted({item["evidence_id"] for item in excluded})
        selected_ids = {unit["evidence_id"] for unit, _, _, _ in selected}
        conflict_coverage = [
            _group_coverage(group, selected_ids, excluded)
            for group in coverage_groups
            if group["kind"] == "conflict"
        ]
        coverage_details = [
            _group_coverage(group, selected_ids, excluded)
            for group in coverage_groups
        ]
        conflict_included = all(
            item["complete"] for item in conflict_coverage
        )
        coverage_complete = all(item["complete"] for item in coverage_details)
        return {
            "status": status,
            "selected_records": selected_records_copy,
            "selected_supporting_evidence": selected_supporting,
            "selected_independent_evidence": selected_independent,
            "selection_metadata": {
                "budget": {
                    "max_evidence_units": config.max_evidence_units,
                    "max_characters": config.max_characters,
                    "max_records": config.max_records,
                    "max_characters_per_unit": config.max_characters_per_unit,
                },
                "selected_count": len(selected),
                "selected_supporting_count": len(selected_supporting),
                "selected_independent_count": len(selected_independent),
                "excluded_count": len(excluded),
                "excluded_evidence_ids": excluded_ids,
                "excluded_evidence": excluded,
                "excluded_record_ids": [],
                "truncated": bool(excluded),
                "coverage": {
                    "record_coverage_complete": True,
                    "supporting_coverage_complete": not any(
                        item["role"] == "supporting" for item in excluded
                    ),
                    "independent_coverage_complete": not any(
                        item["role"] == "independent" for item in excluded
                    ),
                    "conflict_coverage_complete": conflict_included,
                    "conflict_groups": conflict_coverage,
                    "coverage_groups": coverage_details,
                    "coverage_complete": coverage_complete,
                },
                "evidence_needed_to_answer": sorted(
                    unit["evidence_id"]
                    for unit, _, reasons, _ in selected
                    if "record_support" in reasons
                ),
                "evidence_included_for_conflict": sorted(conflict_ids & selected_ids),
                "conflict_flags": conflicts,
                "warnings": (
                    ["Conflict evidence was excluded by budget."]
                    if not conflict_included
                    else []
                ),
                "characters_used": chars,
            },
        }


def _empty_result(
    status: str, config: EvidenceSelectionConfig, records: int, evidence: int
) -> dict[str, Any]:
    return {
        "status": status,
        "selected_records": [],
        "selected_supporting_evidence": [],
        "selected_independent_evidence": [],
        "selection_metadata": {
            "budget": {
                "max_evidence_units": config.max_evidence_units,
                "max_characters": config.max_characters,
                "max_records": config.max_records,
                "max_characters_per_unit": config.max_characters_per_unit,
            },
            "selected_count": 0,
            "selected_supporting_count": 0,
            "selected_independent_count": 0,
            "excluded_count": evidence,
            "excluded_evidence_ids": [],
            "excluded_evidence": [],
            "excluded_record_ids": [],
            "truncated": False,
            "coverage": {
                "record_coverage_complete": records == 0,
                "supporting_coverage_complete": True,
                "independent_coverage_complete": True,
                "conflict_coverage_complete": True,
                "conflict_groups": [],
                "coverage_groups": [],
                "coverage_complete": records == 0 and evidence == 0,
            },
            "evidence_needed_to_answer": [],
            "evidence_included_for_conflict": [],
            "conflict_flags": [],
            "warnings": [],
            "characters_used": 0,
        },
    }


def _deduplicate_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for unit in units:
        if not isinstance(unit, dict) or "evidence_id" not in unit:
            continue
        evidence_id = unit["evidence_id"]
        if evidence_id in unique:
            if unique[evidence_id] != unit:
                raise ValueError(
                    f"Conflicting duplicate evidence_id: {evidence_id}"
                )
        else:
            unique[evidence_id] = unit
    return [unique[key] for key in sorted(unique)]


def _validate_cross_role_duplicates(
    supporting: list[dict[str, Any]], independent: list[dict[str, Any]]
) -> None:
    supporting_by_id = {unit["evidence_id"]: unit for unit in supporting}
    for unit in independent:
        original = supporting_by_id.get(unit["evidence_id"])
        if original is not None and original != unit:
            raise ValueError(
                f"Conflicting duplicate evidence_id: {unit['evidence_id']}"
            )


def _exclusion(
    evidence_id: str, role: str, reasons: list[str], reason: str
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "role": role,
        "reasons": reasons,
        "reason": reason,
    }


def _context(
    records: list[dict[str, Any]],
    selected: list[tuple[dict[str, Any], str, list[str], dict[str, Any] | None]],
) -> dict[str, Any]:
    return {
        "records": records,
        "supporting_evidence": [
            unit for unit, role, _, _ in selected if role == "supporting"
        ],
        "independent_evidence": [
            unit for unit, role, _, _ in selected if role == "independent"
        ],
    }


def _serialized_length(value: Any) -> int:
    return len(
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def _tokens(*values: Any) -> list[str]:
    return re.findall(r"\w+", " ".join(str(value) for value in values if value))


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def _record_dates(record: dict[str, Any]) -> list[str]:
    return [
        str(value)
        for key, value in record.get("attributes", {}).items()
        if "date" in key and value
    ]


def _date_role_matches(record: dict[str, Any], role: str) -> bool:
    fields = {
        "meeting_date": {"meeting", "attendance"},
        "event_date": {"event"},
        "start_date": {"event"},
        "end_date": {"event"},
    }
    return record.get("record_type") in fields.get(role, set())


def _specificity(unit: dict[str, Any]) -> int:
    if "cell" in unit:
        return 8
    if "row" in unit or "cell_range" in unit:
        return 6
    if "page" in unit:
        return 4
    return 0


def _detect_conflicts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts = []
    for record in records:
        observations = record.get("attributes", {}).get("participant_observations", [])
        values = {
            item.get("source_statement")
            for item in observations
            if item.get("source_statement")
        }
        if len(values) > 1:
            evidence_ids = sorted(
                item.get("evidence_id")
                for item in observations
                if item.get("evidence_id")
            )
            signature = "|".join(evidence_ids) + "|participant_category"
            conflicts.append(
                {
                "conflict_group_id": "conflict:"
                + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16],
                "record_id": record.get("record_id"),
                "dimension": "participant_category",
                "values": sorted(values),
                "evidence_ids": evidence_ids,
                }
            )
    return conflicts


def _derive_coverage_groups(
    records: list[dict[str, Any]],
    units: list[tuple[dict[str, Any], str]],
    record_by_evidence: dict[str, dict[str, Any]],
    filters: dict[str, Any],
    query_understanding: dict[str, Any],
) -> list[dict[str, Any]]:
    """Derive deterministic groups whose members should be considered together."""
    unit_ids = {unit["evidence_id"] for unit, _ in units}
    groups: list[dict[str, Any]] = []
    for conflict in _detect_conflicts(records):
        ids = sorted(unit_ids & set(conflict["evidence_ids"]))
        if len(ids) > 1:
            groups.append(
                {
                "coverage_group_id": conflict["conflict_group_id"],
                "kind": "conflict",
                "evidence_ids": ids,
                "reason": "participant observations differ across selected evidence.",
                }
            )

    if query_understanding.get("intent") == "date_activity":
        date = filters.get("date")
        date_records = [
            record
            for record in records
            if date and date in _record_dates(record)
        ]
        for record in date_records:
            attrs = record.get("attributes", {})
            if record.get("record_type") != "meeting":
                continue
            meeting_type = str(attrs.get("meeting_type", "")).casefold()
            if not any(term in meeting_type for term in ("planning", "scheduled")):
                continue
            companions = [
                candidate
                for candidate in date_records
                if candidate is not record
                and candidate.get("record_type") == "event"
                and candidate.get("attributes", {}).get("status")
            ]
            for companion in companions:
                ids = sorted(
                    evidence_id
                    for evidence_id, candidate in record_by_evidence.items()
                    if candidate in (record, companion) and evidence_id in unit_ids
                )
                if len(ids) > 1:
                    groups.append(
                        {
                            "coverage_group_id": _stable_group_id(
                                "lifecycle", ids
                            ),
                            "kind": "lifecycle",
                            "evidence_ids": ids,
                            "reason": "records describe related lifecycle stages.",
                        }
                    )
    return sorted(groups, key=lambda group: group["coverage_group_id"])


def _primary_date_activity_ids(
    units: list[tuple[dict[str, Any], str]],
    record_by_evidence: dict[str, dict[str, Any]],
    query_understanding: dict[str, Any],
    date: Any,
) -> set[str]:
    if query_understanding.get("intent") != "date_activity" or not date:
        return set()
    chosen: dict[str, str] = {}
    for unit, _ in sorted(units, key=lambda item: item[0]["evidence_id"]):
        record = record_by_evidence.get(unit["evidence_id"])
        if record is None or date not in _record_dates(record):
            continue
        record_type = record.get("record_type")
        if record_type in {"meeting", "event", "attendance"}:
            chosen.setdefault(record_type, unit["evidence_id"])
    return set(chosen.values())


def _stable_group_id(kind: str, evidence_ids: list[str]) -> str:
    signature = kind + "|" + "|".join(sorted(evidence_ids))
    return "coverage:" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]


def _group_coverage(
    group: dict[str, Any],
    selected_ids: set[str],
    excluded: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_ids = sorted(group["evidence_ids"])
    excluded_ids = sorted(
        evidence_id
        for evidence_id in evidence_ids
        if evidence_id not in selected_ids
    )
    return {
        "coverage_group_id": group["coverage_group_id"],
        "kind": group["kind"],
        "evidence_ids": evidence_ids,
        "selected_evidence_ids": sorted(selected_ids & set(evidence_ids)),
        "excluded_evidence_ids": excluded_ids,
        "reason": group["reason"],
        "complete": not excluded_ids,
    }
