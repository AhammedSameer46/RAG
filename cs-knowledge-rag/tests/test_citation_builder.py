import copy
import unittest
from pathlib import Path

from cs_ingest.answer_contract import validate_answer
from cs_ingest.citation_builder import CitationBuilder, CitationBuilderError, citation_handles
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class CitationBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.response = build_evidence_response(
            pipeline.run("What happened on 18 July 2026?")
        )
        cls.builder = CitationBuilder()

    def test_deterministic_e1_and_e2_mapping(self):
        handles = citation_handles(self.response)
        self.assertEqual(list(handles)[:2], ["E1", "E2"])
        self.assertEqual(list(handles), list(citation_handles(self.response)))
        for ref, evidence in handles.items():
            result = self.builder.build(
                {"status": "answered", "claims": [{"text": "Grounded.", "citation_refs": [ref]}]},
                self.response,
            )
            self.assertEqual(result["citations"][0]["evidence_id"], evidence["evidence_id"])

    def test_multiple_refs_and_exact_provenance(self):
        handles = citation_handles(self.response)
        result = self.builder.build(
            {"status": "answered", "claims": [{"text": "Grounded.", "citation_refs": ["E1", "E2"]}]},
            self.response,
        )
        self.assertEqual(
            result["citations"][1]["location"],
            {
                field: handles["E2"][field]
                for field in ("page", "sheet", "row", "cell", "cell_range")
                if field in handles["E2"]
            },
        )
        self.assertEqual(validate_answer(result, self.response), {"valid": True, "errors": []})

    def test_pdf_and_spreadsheet_provenance_are_copied_exactly(self):
        response = {
            "answer_context": {
                "records": [],
                "supporting_evidence": [
                    {
                        "evidence_id": "pdf-evidence",
                        "source_id": "pdf-source",
                        "filename": "minutes.pdf",
                        "page": 4,
                    },
                    {
                        "evidence_id": "sheet-evidence",
                        "source_id": "sheet-source",
                        "filename": "attendance.xlsx",
                        "sheet": "Faculty Attendance",
                        "row": 6,
                        "cell": "B6",
                        "cell_range": "A6:C6",
                    },
                ],
                "independent_evidence": [],
            }
        }
        result = self.builder.build(
            {
                "status": "answered",
                "claims": [{"text": "Grounded.", "citation_refs": ["E1", "E2"]}],
            },
            response,
        )
        self.assertEqual(result["citations"][0]["location"], {"page": 4})
        self.assertEqual(
            result["citations"][1]["location"],
            {
                "sheet": "Faculty Attendance",
                "row": 6,
                "cell": "B6",
                "cell_range": "A6:C6",
            },
        )

    def test_unknown_duplicate_and_malformed_refs_are_rejected(self):
        for refs in (["E99"], ["E1", "E1"], [1]):
            with self.assertRaises(CitationBuilderError):
                self.builder.build(
                    {"status": "answered", "claims": [{"text": "Grounded.", "citation_refs": refs}]},
                    self.response,
                )

    def test_excluded_evidence_cannot_be_referenced(self):
        with self.assertRaises(CitationBuilderError):
            self.builder.build(
                {"status": "answered", "claims": [{"text": "Grounded.", "citation_refs": ["E99"]}]},
                self.response,
            )

    def test_non_answerable_statuses_build_empty_final_contracts(self):
        for status in ("clarification_required", "insufficient_evidence"):
            self.assertEqual(
                self.builder.build(
                    {"status": status, "claims": []},
                    self.response,
                ),
                {"status": status, "answer": "", "citations": []},
            )

    def test_input_is_immutable_and_final_shape_has_no_internal_field(self):
        before = copy.deepcopy(self.response)
        result = self.builder.build(
            {"status": "answered", "claims": [{"text": "Grounded.", "citation_refs": ["E1"]}]},
            self.response,
        )
        self.assertEqual(self.response, before)
        self.assertEqual(set(result), {"status", "answer", "citations"})
