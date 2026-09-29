import unittest
from copy import deepcopy
from pathlib import Path

from cs_ingest.answer_contract import validate_answer
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class AnswerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.date_response = build_evidence_response(
            cls.pipeline.run("What happened on 18 July 2026?")
        )
        cls.event_response = build_evidence_response(
            cls.pipeline.run("Who coordinated C-START?")
        )
        cls.keyword_response = build_evidence_response(
            cls.pipeline.run("What was discussed about lab procurement?")
        )
        cls.insufficient_response = build_evidence_response(
            cls.pipeline.run("What happened on 10 January 2099?")
        )
        cls.clarification_response = build_evidence_response(
            cls.pipeline.run("What happened on 18 July?")
        )

    @staticmethod
    def _citation(evidence):
        location = {
            field: evidence[field]
            for field in ("page", "sheet", "row", "cell", "cell_range")
            if field in evidence
        }
        return {
            "evidence_id": evidence["evidence_id"],
            "source_id": evidence["source_id"],
            "filename": evidence["filename"],
            "location": location,
        }

    def test_valid_pdf_answer(self):
        evidence = next(
            item
            for item in self.event_response["answer_context"]["supporting_evidence"]
            if item["kind"] == "pdf_page"
        )
        result = validate_answer(
            {
                "status": "answered",
                "answer": "The retrieved evidence identifies the coordinator.",
                "citations": [self._citation(evidence)],
            },
            self.event_response,
        )
        self.assertEqual(result, {"valid": True, "errors": []})

    def test_valid_excel_answer_with_sheet_row_cell(self):
        evidence = next(
            item
            for item in self.date_response["answer_context"]["supporting_evidence"]
            if item["kind"] == "worksheet_cell"
        )
        result = validate_answer(
            {
                "status": "answered",
                "answer": "The attendance evidence was retrieved.",
                "citations": [self._citation(evidence)],
            },
            self.date_response,
        )
        self.assertTrue(result["valid"])

    def test_unknown_evidence_id_is_rejected(self):
        result = validate_answer(
            {
                "status": "answered",
                "answer": "A claim.",
                "citations": [
                    {
                        "evidence_id": "not-retrieved",
                        "source_id": "source",
                        "filename": "file.pdf",
                        "location": {"page": 1},
                    }
                ],
            },
            self.date_response,
        )
        self.assertIn("UNKNOWN_EVIDENCE_ID", {error["code"] for error in result["errors"]})

    def test_wrong_source_filename_and_pdf_page_are_rejected(self):
        evidence = next(
            item
            for item in self.event_response["answer_context"]["supporting_evidence"]
            if item["kind"] == "pdf_page"
        )
        citation = self._citation(evidence)
        citation["source_id"] = "wrong-source"
        citation["filename"] = "wrong.pdf"
        citation["location"]["page"] = evidence["page"] + 1
        result = validate_answer(
            {"status": "answered", "answer": "A claim.", "citations": [citation]},
            self.event_response,
        )
        codes = {error["code"] for error in result["errors"]}
        self.assertTrue({"WRONG_SOURCE_ID", "WRONG_FILENAME", "WRONG_LOCATION"} <= codes)

    def test_wrong_spreadsheet_location_is_rejected(self):
        evidence = next(
            item
            for item in self.date_response["answer_context"]["supporting_evidence"]
            if item["kind"] == "worksheet_cell"
        )
        citation = self._citation(evidence)
        citation["location"]["sheet"] = "Wrong Sheet"
        citation["location"]["row"] = evidence["row"] + 1
        citation["location"]["cell"] = "Z99"
        result = validate_answer(
            {"status": "answered", "answer": "A claim.", "citations": [citation]},
            self.date_response,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(
            {error["code"] for error in result["errors"]}, {"WRONG_LOCATION"}
        )

    def test_answered_requires_text_and_citation(self):
        result = validate_answer(
            {"status": "answered", "answer": "", "citations": []},
            self.date_response,
        )
        codes = {error["code"] for error in result["errors"]}
        self.assertTrue({"EMPTY_ANSWER", "NO_CITATIONS"} <= codes)

    def test_insufficient_evidence_without_answer_or_citations_is_valid(self):
        result = validate_answer(
            {"status": "insufficient_evidence", "answer": "", "citations": []},
            self.insufficient_response,
        )
        self.assertEqual(result, {"valid": True, "errors": []})

    def test_insufficient_evidence_factual_answer_is_rejected(self):
        result = validate_answer(
            {"status": "insufficient_evidence", "answer": "A fact.", "citations": []},
            self.insufficient_response,
        )
        self.assertIn(
            "FACTUAL_ANSWER_NOT_ALLOWED",
            {error["code"] for error in result["errors"]},
        )

    def test_clarification_without_answer_or_citations_is_valid(self):
        result = validate_answer(
            {"status": "clarification_required", "answer": "", "citations": []},
            self.clarification_response,
        )
        self.assertEqual(result, {"valid": True, "errors": []})

    def test_clarification_factual_answer_is_rejected(self):
        result = validate_answer(
            {"status": "clarification_required", "answer": "A fact.", "citations": []},
            self.clarification_response,
        )
        self.assertIn(
            "FACTUAL_ANSWER_NOT_ALLOWED",
            {error["code"] for error in result["errors"]},
        )

    def test_independent_evidence_can_be_cited_without_becoming_supporting(self):
        evidence = next(
            item
            for item in self.keyword_response["answer_context"]["independent_evidence"]
            if item["evidence_id"]
            not in {
                support["evidence_id"]
                for support in self.keyword_response["answer_context"]["supporting_evidence"]
            }
        )
        result = validate_answer(
            {
                "status": "answered",
                "answer": "An independently matched observation.",
                "citations": [self._citation(evidence)],
            },
            self.keyword_response,
        )
        self.assertTrue(result["valid"])
        self.assertFalse(
            evidence["evidence_id"]
            in {
                item["evidence_id"]
                for item in self.keyword_response["answer_context"]["supporting_evidence"]
            }
        )

    def test_outside_evidence_package_is_rejected(self):
        evidence = self.date_response["answer_context"]["supporting_evidence"][0]
        citation = self._citation(evidence)
        citation["evidence_id"] += ":outside"
        result = validate_answer(
            {"status": "answered", "answer": "A claim.", "citations": [citation]},
            self.date_response,
        )
        self.assertFalse(result["valid"])
        self.assertIn("UNKNOWN_EVIDENCE_ID", {error["code"] for error in result["errors"]})

    def test_validation_does_not_modify_evidence_response(self):
        original = deepcopy(self.date_response)
        evidence = self.date_response["answer_context"]["supporting_evidence"][0]
        validate_answer(
            {
                "status": "answered",
                "answer": "A claim.",
                "citations": [self._citation(evidence)],
            },
            self.date_response,
        )
        self.assertEqual(self.date_response, original)


if __name__ == "__main__":
    unittest.main()
