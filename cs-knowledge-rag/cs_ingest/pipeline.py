"""Deterministic query-understanding to retrieval orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .query_understanding import QueryUnderstanding
from .retrieval import Retriever

_RETRIEVER_FILTERS = {
    "date",
    "record_type",
    "person",
    "event_name",
    "date_role",
    "keyword",
}


class QueryRetrievalPipeline:
    """Interpret a question and, only when safe, execute deterministic retrieval."""

    def __init__(
        self,
        query_understanding: QueryUnderstanding,
        retriever: Retriever,
    ) -> None:
        self.query_understanding = query_understanding
        self.retriever = retriever

    @classmethod
    def from_json(cls, path: str | Path) -> "QueryRetrievalPipeline":
        normalized_path = Path(path)
        return cls(
            QueryUnderstanding.from_json(normalized_path),
            Retriever.from_json(normalized_path),
        )

    def run(self, question: str) -> dict[str, Any]:
        understanding = self.query_understanding.understand(question)
        empty_retrieval = {
            "records": [],
            "supporting_evidence_units": [],
            "matched_evidence_units": [],
            "has_evidence": False,
        }
        unsupported_filters = set(understanding["filters"]) - _RETRIEVER_FILTERS
        if (
            understanding["confidence"] != "high"
            or understanding["ambiguities"]
            or understanding["unresolved"]
            or unsupported_filters
        ):
            if unsupported_filters:
                understanding["unresolved"].append(
                    "Unsupported retrieval filters: "
                    + ", ".join(sorted(unsupported_filters))
                )
            return {
                "question": question,
                "query_understanding": understanding,
                "retrieval": empty_retrieval,
                "status": "clarification_required",
            }

        filters = {
            key: value
            for key, value in understanding["filters"].items()
            if key in _RETRIEVER_FILTERS
        }
        retrieval = self.retriever.query(**filters)
        return {
            "question": question,
            "query_understanding": understanding,
            "retrieval": {
                "records": retrieval["records"],
                "supporting_evidence_units": retrieval["supporting_evidence_units"],
                "matched_evidence_units": retrieval["matched_evidence_units"],
                "has_evidence": retrieval["has_evidence"],
            },
            "status": (
                "answerable" if retrieval["has_evidence"] else "insufficient_evidence"
            ),
        }


def run_query(question: str, normalized_path: str | Path) -> dict[str, Any]:
    """Run one question through deterministic understanding and retrieval."""
    return QueryRetrievalPipeline.from_json(normalized_path).run(question)


def write_result(
    question: str,
    normalized_path: str | Path,
    output_path: str | Path,
) -> None:
    """Serialize one pipeline result deterministically."""
    result = run_query(question, normalized_path)
    Path(output_path).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
