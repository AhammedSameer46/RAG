"""Deterministic conversion of institutional questions into retrieval requests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .ingest import normalize_date

_DATE_RE = re.compile(
    r"\b(?:\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-[A-Za-z]{3}-\d{4}|"
    r"\d{1,2}\s+[A-Za-z]+\s+\d{4})\b"
)
_MONTH_DAY_RE = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\b",
    re.IGNORECASE,
)
_PERSON_RE = re.compile(
    r"\b(?P<name>(?:Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)\b"
)
_ROLE_PHRASES = (
    (("next meeting",), "next_meeting_date"),
    (("original date", "originally scheduled"), "original_date"),
    (("rescheduled date", "rescheduled", "moved to"), "rescheduled_date"),
    (("issued on", "notice issued", "notice circulated"), "document_issue_date"),
    (("report submitted", "report submission"), "report_submission_date"),
)
class QueryUnderstanding:
    """Interpret a question without retrieving or generating an answer."""

    def __init__(self, known_people: set[str] | None = None, known_events: set[str] | None = None):
        self.known_people = known_people
        self.known_events = known_events

    @classmethod
    def from_json(cls, path: str | Path) -> "QueryUnderstanding":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        people = {
            record["attributes"]["person"]
            for record in data["records"]
            if record["record_type"] == "attendance"
        }
        events = {
            record["attributes"]["name"]
            for record in data["records"]
            if record["record_type"] == "event"
        }
        return cls(people, events)

    def understand(self, question: str) -> dict[str, Any]:
        text = question.strip()
        lowered = text.casefold()
        result: dict[str, Any] = {
            "intent": "unknown",
            "retrieval_mode": "exact",
            "filters": {},
            "keywords": [],
            "ambiguities": [],
            "unresolved": [],
            "confidence": "low",
        }
        if not text:
            result["ambiguities"].append("Question is empty")
            result["unresolved"].append("No retrieval request can be formed")
            return result

        self._extract_date(text, lowered, result)
        self._extract_date_role(lowered, result)
        self._extract_person(text, result)
        self._infer_intent(lowered, result)
        self._extract_constraints(text, lowered, result)
        self._set_mode(result)
        self._apply_bounded_limitations(lowered, result)
        self._set_confidence(result)
        return result

    def _extract_date(self, text: str, lowered: str, result: dict[str, Any]) -> None:
        full_dates = list(_DATE_RE.finditer(text))
        if full_dates:
            normalized = normalize_date(full_dates[0].group(0))
            if normalized:
                result["filters"]["date"] = normalized
            return
        if _MONTH_DAY_RE.search(text):
            result["ambiguities"].append("Year is missing from the date")
            result["unresolved"].append("Exact date retrieval requires a year")
        if re.search(r"\b(between|from)\b.+\b(?:and|to)\b", lowered) or re.search(
            r"\bduring\s+(?:january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\b",
            lowered,
        ):
            result["ambiguities"].append("Date range was requested")
            result["unresolved"].append("Date-range retrieval is not supported by the current Retriever")

    def _extract_date_role(self, lowered: str, result: dict[str, Any]) -> None:
        matches = [role for phrases, role in _ROLE_PHRASES if any(phrase in lowered for phrase in phrases)]
        if len(set(matches)) == 1:
            result["filters"]["date_role"] = matches[0]
        elif len(set(matches)) > 1:
            result["ambiguities"].append("Multiple date roles were requested")
            result["unresolved"].append("A single date role could not be selected safely")
        elif "when was the meeting" in lowered and "meeting date" not in lowered:
            result["ambiguities"].append("The meeting date role is unspecified")
            result["unresolved"].append("Original, rescheduled, and actual meeting dates are not distinguished")

    def _extract_person(self, text: str, result: dict[str, Any]) -> None:
        match = _PERSON_RE.search(text)
        if not match:
            if re.search(
                r"\b(?:[Ww]as|[Dd]id|[Ww]hich meetings did)\s+[A-Z][a-z]+\b",
                text,
            ):
                result["ambiguities"].append("Person identity is incomplete")
                result["unresolved"].append("A full source-form person name is required")
            return
        person = match.group("name")
        result["filters"]["person"] = person
        if self.known_people is not None and person not in self.known_people:
            result["ambiguities"].append(f"Person is not present in the known sample records: {person}")
            result["unresolved"].append("Person identity could not be verified without fuzzy matching")

    def _infer_intent(self, lowered: str, result: dict[str, Any]) -> None:
        if "which meetings" in lowered and "attend" in lowered:
            result["intent"] = "person_activity"
        elif "who attended" in lowered and "event" in lowered:
            result["intent"] = "event_lookup"
        elif any(word in lowered for word in ("present", "absent", "attendance", "attend")):
            result["intent"] = "attendance_lookup"
        elif any(phrase in lowered for phrase in ("what happened", "activity on")):
            result["intent"] = "date_activity" if result["filters"].get("date") else "unknown"
        elif "rescheduled" in lowered or "original date" in lowered or "next meeting" in lowered:
            result["intent"] = "date_role_lookup"
        elif "coordinat" in lowered or "participat" in lowered or "event" in lowered:
            result["intent"] = "event_lookup"
        elif "what meeting" in lowered or "which meeting" in lowered:
            result["intent"] = "meeting_lookup"
        elif any(word in lowered for word in ("discussed", "decisions", "decision", "regarding")):
            result["intent"] = "narrative_search"
        elif any(word in lowered for word in ("how many", "what was", "what is", "when was")):
            result["intent"] = "structured_fact"

    def _extract_constraints(self, text: str, lowered: str, result: dict[str, Any]) -> None:
        if "department meeting" in lowered and result["filters"].get("record_type") == "attendance":
            result["unresolved"].append("The current Retriever cannot filter attendance by meeting type")
        if "department meeting" in lowered and "attendance" in result["intent"]:
            result["ambiguities"].append("Meeting type was specified but is not an executable attendance filter")
            if "The current Retriever cannot filter attendance by meeting type" not in result["unresolved"]:
                result["unresolved"].append("The current Retriever cannot filter attendance by meeting type")
        if any(word in lowered for word in ("present", "absent", "attendance", "attend")):
            result["filters"]["record_type"] = "attendance"
        elif "meeting" in lowered and result["intent"] == "meeting_lookup":
            result["filters"]["record_type"] = "meeting"
        event_match = next(
            (event for event in self.known_events or set() if event in text),
            None,
        )
        if event_match:
            result["filters"]["record_type"] = "event"
            result["filters"]["event_name"] = event_match
        elif "c-start" in lowered:
            result["filters"]["record_type"] = "event"
            result["keywords"].append("C-START")
        if "fdp" in lowered:
            result["keywords"].append("FDP")
        if "lab procurement" in lowered:
            result["keywords"].extend(["lab", "procurement"])
        if result["intent"] == "date_role_lookup" and "faculty meeting" in lowered:
            result["keywords"].append("faculty meeting")
        result["keywords"] = list(dict.fromkeys(result["keywords"]))
        if result["keywords"]:
            result["filters"]["keyword"] = " ".join(result["keywords"])

    def _set_mode(self, result: dict[str, Any]) -> None:
        has_exact = bool(set(result["filters"]) - {"keyword"})
        has_keywords = bool(result["keywords"])
        if has_exact and has_keywords and result["intent"] == "date_activity":
            result["intent"] = "mixed_query"
        if has_exact and has_keywords:
            result["retrieval_mode"] = "exact_and_keyword"
        elif has_keywords:
            result["retrieval_mode"] = "keyword"
        else:
            result["retrieval_mode"] = "exact"

    def _apply_bounded_limitations(self, lowered: str, result: dict[str, Any]) -> None:
        if "which meetings did" in lowered and result["intent"] == "person_activity":
            result["filters"]["record_type"] = "attendance"
            result["unresolved"].append("Attendance coverage is limited to the meetings represented in the sample attendance sheet")
        if "who attended" in lowered and "event" in lowered:
            result["unresolved"].append("The sample does not contain a complete event attendee list")
        if result["intent"] == "event_lookup" and "event_name" not in result["filters"] and not result["keywords"]:
            result["ambiguities"].append("Event name is unspecified or ambiguous")
            result["unresolved"].append("A specific event name is required")
        if result["intent"] == "unknown" and not result["filters"] and not result["keywords"]:
            result["ambiguities"].append("Question is too broad to map to a bounded retrieval request")
            result["unresolved"].append("A specific date, person, event, topic, or record type is required")

    def _set_confidence(self, result: dict[str, Any]) -> None:
        if result["ambiguities"] or result["unresolved"]:
            result["confidence"] = "low" if not result["filters"] else "medium"
        elif result["intent"] != "unknown":
            result["confidence"] = "high"


def understand_query(question: str, normalized_path: str | Path | None = None) -> dict[str, Any]:
    interpreter = (
        QueryUnderstanding.from_json(normalized_path)
        if normalized_path is not None
        else QueryUnderstanding()
    )
    return interpreter.understand(question)
