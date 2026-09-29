import unittest
from copy import deepcopy
from pathlib import Path

from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class EvidenceResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )

    def test_date_activity_preserves_records_and_multiple_evidence(self):
        result = build_evidence_response(
            self.pipeline.run("What happened on 18 July 2026?")
        )
        self.assertEqual(result["status"], "answerable")
        self.assertGreater(len(result["answer_context"]["records"]), 1)
        self.assertGreater(len(result["answer_context"]["supporting_evidence"]), 1)
        self.assertTrue(result["coverage"]["has_records"])
        self.assertTrue(result["sources"])

    def test_cstart_preserves_supporting_provenance(self):
        result = build_evidence_response(self.pipeline.run("Who coordinated C-START?"))
        supporting = result["answer_context"]["supporting_evidence"]
        self.assertTrue(supporting)
        self.assertTrue(
            all(
                item["source_id"] and item["evidence_id"] and item["filename"]
                for item in supporting
            )
        )
        self.assertTrue(any(item["kind"] == "pdf_page" for item in supporting))
        self.assertEqual(
            sorted(
                evidence_id
                for source in result["sources"]
                for evidence_id in source["evidence_ids"]
            ),
            sorted({item["evidence_id"] for item in supporting + result["answer_context"]["independent_evidence"]}),
        )

    def test_lab_procurement_keeps_independent_evidence_separate(self):
        result = build_evidence_response(
            self.pipeline.run("What was discussed about lab procurement?")
        )
        supporting = result["answer_context"]["supporting_evidence"]
        independent = result["answer_context"]["independent_evidence"]
        self.assertTrue(supporting)
        self.assertTrue(independent)
        self.assertTrue(any(item["kind"] == "pdf_page" for item in independent))
        self.assertFalse(
            any(
                item["kind"] == "pdf_page"
                and item["filename"] == "CS_Dept_Meeting_Minutes_18Jul2026.pdf"
                for item in supporting
            )
        )

    def test_insufficient_evidence_has_empty_context(self):
        result = build_evidence_response(
            self.pipeline.run("What happened on 10 January 2099?")
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["answer_context"]["records"], [])
        self.assertEqual(result["answer_context"]["supporting_evidence"], [])
        self.assertEqual(result["answer_context"]["independent_evidence"], [])
        self.assertEqual(result["sources"], [])
        self.assertFalse(result["coverage"]["has_records"])

    def test_clarification_preserves_query_understanding_without_context(self):
        pipeline_result = self.pipeline.run("What happened on 18 July?")
        result = build_evidence_response(pipeline_result)
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["answer_context"]["records"], [])
        self.assertEqual(result["answer_context"]["supporting_evidence"], [])
        self.assertEqual(result["answer_context"]["independent_evidence"], [])
        self.assertEqual(
            result["query_understanding"], pipeline_result["query_understanding"]
        )
        self.assertTrue(result["query_understanding"]["unresolved"])
        self.assertEqual(result["sources"], [])

    def test_duplicate_evidence_ids_are_retained_once_per_collection(self):
        pipeline_result = self.pipeline.run("Who coordinated C-START?")
        duplicate = deepcopy(
            pipeline_result["retrieval"]["supporting_evidence_units"][0]
        )
        pipeline_result["retrieval"]["supporting_evidence_units"].append(duplicate)
        result = build_evidence_response(pipeline_result)
        evidence = result["answer_context"]["supporting_evidence"]
        self.assertEqual(
            len(evidence), len({item["evidence_id"] for item in evidence})
        )

    def test_pdf_and_excel_provenance_survives_unchanged(self):
        pipeline_result = self.pipeline.run("What happened on 18 July 2026?")
        result = build_evidence_response(pipeline_result)
        evidence = (
            result["answer_context"]["supporting_evidence"]
            + result["answer_context"]["independent_evidence"]
        )
        pdf = next(item for item in evidence if item["kind"] == "pdf_page")
        spreadsheet = next(item for item in evidence if item["kind"] == "worksheet_row")
        self.assertIn("page", pdf)
        self.assertIn("sheet", spreadsheet)
        self.assertIn("row", spreadsheet)
        attendance = build_evidence_response(
            self.pipeline.run(
                "What happened on 18 July 2026?"
            )
        )
        self.assertTrue(
            any(
                item["kind"] == "worksheet_cell" and "cell" in item
                for item in (
                    attendance["answer_context"]["supporting_evidence"]
                    + attendance["answer_context"]["independent_evidence"]
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
