"""End-to-end deterministic evidence-to-answer contract orchestration."""

from __future__ import annotations

from pathlib import Path
import inspect
from typing import Any

from .answer_generator import AnswerGenerator
from .answer_contract import validate_answer
from .evidence_response import build_evidence_response
from .mock_answer_generator import MockAnswerGenerator
from .pipeline import QueryRetrievalPipeline


class AnswerPipeline:
    def __init__(
        self,
        query_pipeline: QueryRetrievalPipeline,
        answer_generator: AnswerGenerator | None = None,
    ) -> None:
        self.query_pipeline = query_pipeline
        self.answer_generator = answer_generator or MockAnswerGenerator()

    @classmethod
    def from_json(cls, path: str | Path) -> "AnswerPipeline":
        return cls(QueryRetrievalPipeline.from_json(path))

    def run(self, question: str) -> dict[str, Any]:
        evidence_response = build_evidence_response(
            self.query_pipeline.run(question)
        )
        if evidence_response["status"] in {
            "insufficient_evidence",
            "clarification_required",
        }:
            answer = {
                "status": evidence_response["status"],
                "answer": "",
                "citations": [],
            }
        else:
            answer = _generate(self.answer_generator, question, evidence_response)
        validation = validate_answer(answer, evidence_response)
        return {
            "question": question,
            "evidence_response": evidence_response,
            "answer": answer,
            "validation": validation,
        }


def _generate(
    generator: AnswerGenerator,
    question: str,
    evidence_response: dict[str, Any],
) -> dict[str, Any]:
    """Call the current interface while retaining compatibility with old test doubles."""
    parameters = inspect.signature(generator.generate).parameters
    positional = [
        parameter
        for parameter in parameters.values()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) == 1:
        return generator.generate(evidence_response)  # type: ignore[call-arg]
    return generator.generate(question, evidence_response)
