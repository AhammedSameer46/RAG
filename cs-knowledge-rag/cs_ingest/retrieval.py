"""Deterministic retrieval over normalized local JSON data."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


class Retriever:
    def __init__(self, normalized: dict[str, Any]):
        self.data = normalized
        self.sources = {item["source_id"]: item for item in normalized["sources"]}
        self.evidence = {
            item["evidence_id"]: item for item in normalized["evidence_units"]
        }
        self.date_mentions = normalized["date_mentions"]
        self.records = normalized["records"]

    @classmethod
    def from_json(cls, path: str | Path) -> "Retriever":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def query(
        self,
        *,
        date: str | None = None,
        record_type: str | None = None,
        person: str | None = None,
        event_name: str | None = None,
        date_role: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        """Apply all supplied filters and expand matching records to evidence."""
        if record_type is not None and record_type not in {"meeting", "event", "attendance"}:
            raise ValueError("record_type must be meeting, event, or attendance")

        date_evidence_ids = {
            mention["evidence_id"]
            for mention in self.date_mentions
            if (date is None or mention["normalized_iso"] == date)
            and (date_role is None or mention["date_role"] == date_role)
        }
        matching_records = []
        for record in self.records:
            attributes = record["attributes"]
            matched_fields: list[str] = []
            if record_type is not None and record["record_type"] != record_type:
                continue
            if date is not None and not self._record_matches_date(record, date):
                continue
            elif date is not None:
                matched_fields.append("date")
            if date_role is not None and (
                date is None or not self._record_matches_date_role(record, date_role)
            ):
                continue
            if date_role is not None and date is not None:
                matched_fields.append("date_role")
            if person is not None:
                if record["record_type"] != "attendance" or attributes.get("person") != person:
                    continue
                matched_fields.append("person")
            if event_name is not None:
                if record["record_type"] != "event" or attributes.get("name") != event_name:
                    continue
                matched_fields.append("event_name")
            if keyword is not None:
                record_text = _flatten_text(record)
                if not _contains_keyword(record_text, keyword):
                    continue
                matched_fields.append("record_keyword")
            if not matched_fields:
                matched_fields.append("record")
            matching_records.append(
                {
                    **deepcopy(record),
                    "matched_fields": matched_fields,
                }
            )

        expanded_ids = {
            evidence_ref["evidence_id"]
            for record in matching_records
            for evidence_ref in record["evidence_refs"]
        }
        supporting_ids = set(expanded_ids)
        keyword_evidence_ids = set()
        if keyword is not None:
            keyword_evidence_ids = {
                evidence_id
                for evidence_id, evidence in self.evidence.items()
                if _contains_keyword(_flatten_text(evidence), keyword)
            }
            expanded_ids.update(keyword_evidence_ids)

        date_mention_ids = set()
        if date_role is not None:
            date_mention_ids = date_evidence_ids
            expanded_ids.update(date_evidence_ids)
        if date is not None and not (record_type or person or event_name or keyword):
            date_mention_ids = {
                mention["evidence_id"]
                for mention in self.date_mentions
                if mention["normalized_iso"] == date
            }
            expanded_ids.update(date_mention_ids)

        matching_evidence = []
        supporting_evidence = []
        matched_evidence = []
        for evidence_id in sorted(expanded_ids):
            evidence = self.evidence.get(evidence_id)
            if evidence is None:
                continue
            matched_fields = []
            if evidence_id in supporting_ids:
                matched_fields.append("record_reference")
            if evidence_id in keyword_evidence_ids:
                matched_fields.append("keyword")
            if evidence_id in date_mention_ids:
                matched_fields.append("date_role" if date_role else "date_mention")
            item = {
                **deepcopy(evidence),
                "filename": self.sources[evidence["source_id"]]["filename"],
                "matched_fields": matched_fields,
            }
            matching_evidence.append(item)
            if evidence_id in supporting_ids:
                supporting_evidence.append(deepcopy(item))
            if evidence_id in keyword_evidence_ids or evidence_id in date_mention_ids:
                matched_evidence.append(deepcopy(item))

        return {
            "filters": {
                "date": date,
                "record_type": record_type,
                "person": person,
                "event_name": event_name,
                "date_role": date_role,
                "keyword": keyword,
            },
            "records": matching_records,
            "evidence_units": matching_evidence,
            "supporting_evidence_units": supporting_evidence,
            "matched_evidence_units": matched_evidence,
            "has_evidence": bool(matching_evidence),
        }

    @staticmethod
    def _record_matches_date_role(record: dict[str, Any], role: str) -> bool:
        record_type = record["record_type"]
        attributes = record["attributes"]
        fields_by_role = {
            "meeting_date": {
                "meeting": {"meeting_date"},
                "attendance": {"meeting_date"},
            },
            "event_date": {"event": {"start_date", "end_date"}},
            "start_date": {"event": {"start_date"}},
            "end_date": {"event": {"end_date"}},
        }
        return any(
            attributes.get(field) is not None
            for field in fields_by_role.get(role, {}).get(record_type, set())
        )

    @staticmethod
    def _record_matches_date(record: dict[str, Any], requested: str) -> bool:
        fields_by_type = {
            "meeting": {"meeting_date"},
            "event": {"start_date", "end_date"},
            "attendance": {"meeting_date"},
        }
        fields = fields_by_type.get(record["record_type"], set())
        return any(record["attributes"].get(field) == requested for field in fields)


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _contains_keyword(text: str, query: str) -> bool:
    tokens = re.findall(r"\w+", query.casefold())
    haystack = text.casefold()
    return bool(tokens) and all(token in haystack for token in tokens)


def retrieve_from_json(path: str | Path, **filters: str | None) -> dict[str, Any]:
    return Retriever.from_json(path).query(**filters)
