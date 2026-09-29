"""End-to-end deterministic evidence-to-answer contract orchestration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import inspect
from typing import Any

from .answer_generator import AnswerGenerator
from .answer_contract import validate_answer
from .citation_builder import CitationBuilder
from .evidence_response import build_evidence_response
from .evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from .mock_answer_generator import MockAnswerGenerator
from .pipeline import QueryRetrievalPipeline


class AnswerPipeline:
    def __init__(
        self,
        query_pipeline: QueryRetrievalPipeline,
        answer_generator: AnswerGenerator | None = None,
        evidence_selector: EvidenceSelector | None = None,
        evidence_selection_config: EvidenceSelectionConfig | None = None,
        citation_builder: CitationBuilder | None = None,
    ) -> None:
        if evidence_selection_config is not None and evidence_selector is None:
            raise ValueError(
                "evidence_selection_config requires evidence_selector"
            )
        self.query_pipeline = query_pipeline
        self.answer_generator = answer_generator or MockAnswerGenerator()
        self.evidence_selector = evidence_selector
        self.evidence_selection_config = evidence_selection_config
        self.citation_builder = citation_builder or CitationBuilder()

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        answer_generator: AnswerGenerator | None = None,
        evidence_selector: EvidenceSelector | None = None,
        evidence_selection_config: EvidenceSelectionConfig | None = None,
        citation_builder: CitationBuilder | None = None,
    ) -> "AnswerPipeline":
        return cls(
            QueryRetrievalPipeline.from_json(path),
            answer_generator,
            evidence_selector,
            evidence_selection_config,
            citation_builder,
        )

    def run(self, question: str) -> dict[str, Any]:
        evidence_response = build_evidence_response(
            self.query_pipeline.run(question)
        )
        generator_evidence_response = evidence_response
        if self.evidence_selector is not None:
            selection = self.evidence_selector.select(
                question,
                evidence_response["query_understanding"],
                evidence_response,
                self.evidence_selection_config,  # type: ignore[arg-type]
            )
            generator_evidence_response = _selected_evidence_response(
                evidence_response, selection
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
            answer = _generate(
                self.answer_generator, question, generator_evidence_response
            )
            if "citation_refs" in answer:
                answer = self.citation_builder.build(
                    answer, generator_evidence_response
                )
        validation = validate_answer(answer, generator_evidence_response)
        return {
            "question": question,
            "evidence_response": generator_evidence_response,
            "answer": answer,
            "validation": validation,
        }


def _selected_evidence_response(
    evidence_response: dict[str, Any], selection: dict[str, Any]
) -> dict[str, Any]:
    selected_response = deepcopy(evidence_response)
    selected_response["answer_context"] = {
        "records": deepcopy(selection["selected_records"]),
        "supporting_evidence": deepcopy(
            selection["selected_supporting_evidence"]
        ),
        "independent_evidence": deepcopy(
            selection["selected_independent_evidence"]
        ),
    }
    metadata = deepcopy(selection["selection_metadata"])
    metadata["selected_record_ids"] = [
        record["record_id"] for record in selection["selected_records"]
    ]
    metadata["selected_evidence_ids"] = sorted(
        {
            evidence["evidence_id"]
            for collection in (
                selection["selected_supporting_evidence"],
                selection["selected_independent_evidence"],
            )
            for evidence in collection
        }
    )
    selected_response["selection"] = metadata
    selected_response["coverage"] = deepcopy(metadata["coverage"])
    return selected_response


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
