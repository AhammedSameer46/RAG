import unittest
from pathlib import Path

from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class QueryRetrievalPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )

    def test_date_activity_retrieves_records_and_provenance(self):
        result = self.pipeline.run("What happened on 18 July 2026?")
        self.assertEqual(result["status"], "answerable")
        self.assertEqual(
            result["query_understanding"]["retrieval_mode"], "exact"
        )
        self.assertEqual(
            result["query_understanding"]["filters"]["date"], "2026-07-18"
        )
        self.assertTrue(result["retrieval"]["records"])
        self.assertTrue(result["retrieval"]["supporting_evidence_units"])
        self.assertTrue(
            all(
                "source_id" in item and "evidence_id" in item
                for item in result["retrieval"]["supporting_evidence_units"]
            )
        )

    def test_attendance_query_with_unsupported_meeting_type_requires_clarification(self):
        result = self.pipeline.run(
            "Was Dr. Reena Nair present at the department meeting on 18 July 2026?"
        )
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["retrieval"]["records"], [])
        self.assertTrue(result["query_understanding"]["unresolved"])
        self.assertEqual(
            result["query_understanding"]["filters"]["record_type"], "attendance"
        )
        self.assertEqual(
            result["query_understanding"]["filters"]["person"], "Dr. Reena Nair"
        )

    def test_date_role_query_retrieves_keyword_and_date_role_evidence(self):
        result = self.pipeline.run("When was the faculty meeting rescheduled?")
        self.assertEqual(result["status"], "answerable")
        self.assertEqual(
            result["query_understanding"]["retrieval_mode"], "exact_and_keyword"
        )
        self.assertEqual(len(result["retrieval"]["records"]), 0)
        self.assertTrue(result["retrieval"]["matched_evidence_units"])
        self.assertTrue(
            all("source_id" in item for item in result["retrieval"]["matched_evidence_units"])
        )

    def test_cstart_event_query_retrieves_without_alias_expansion(self):
        result = self.pipeline.run("Who coordinated C-START?")
        self.assertEqual(result["status"], "answerable")
        self.assertEqual(result["query_understanding"]["intent"], "event_lookup")
        self.assertEqual(
            result["query_understanding"]["retrieval_mode"], "exact_and_keyword"
        )
        self.assertNotIn("event_name", result["query_understanding"]["filters"])
        self.assertTrue(result["retrieval"]["matched_evidence_units"])

    def test_lab_procurement_query_preserves_independent_keyword_evidence(self):
        result = self.pipeline.run("What was discussed about lab procurement?")
        self.assertEqual(result["status"], "answerable")
        self.assertEqual(result["query_understanding"]["retrieval_mode"], "keyword")
        self.assertTrue(result["retrieval"]["matched_evidence_units"])
        self.assertTrue(result["retrieval"]["supporting_evidence_units"])
        self.assertTrue(
            any(
                item["kind"] == "pdf_page"
                for item in result["retrieval"]["matched_evidence_units"]
            )
        )

    def test_mixed_date_and_fdp_query_uses_both_constraints(self):
        result = self.pipeline.run(
            "What happened on 10 August 2026 regarding the FDP?"
        )
        self.assertEqual(result["status"], "answerable")
        self.assertEqual(
            result["query_understanding"]["retrieval_mode"], "exact_and_keyword"
        )
        self.assertEqual(
            result["query_understanding"]["filters"]["date"], "2026-08-10"
        )
        self.assertEqual(
            result["query_understanding"]["filters"]["keyword"], "FDP"
        )
        self.assertTrue(result["retrieval"]["records"])

    def test_person_activity_limit_requires_clarification(self):
        result = self.pipeline.run("Which meetings did Prof. Sarah Thomas attend?")
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["retrieval"]["records"], [])
        self.assertTrue(result["query_understanding"]["unresolved"])

    def test_event_attendee_limit_requires_clarification(self):
        result = self.pipeline.run("Who attended the C-START event?")
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["retrieval"]["records"], [])
        self.assertTrue(result["query_understanding"]["unresolved"])

    def test_missing_year_requires_clarification_without_retrieval(self):
        result = self.pipeline.run("What happened on 18 July?")
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["retrieval"]["records"], [])
        self.assertTrue(result["query_understanding"]["ambiguities"])

    def test_broad_question_requires_clarification_without_retrieval(self):
        result = self.pipeline.run("Tell me something about the department.")
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["retrieval"]["records"], [])
        self.assertEqual(result["query_understanding"]["confidence"], "low")

    def test_no_matching_evidence_is_insufficient(self):
        result = self.pipeline.run("What happened on 10 January 2099?")
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertFalse(result["retrieval"]["has_evidence"])
        self.assertEqual(result["retrieval"]["records"], [])

    def test_low_confidence_and_unsupported_filters_cannot_reach_retrieval(self):
        class UnsafeUnderstanding:
            def understand(self, _question):
                del _question
                return {
                    "intent": "unknown",
                    "retrieval_mode": "exact",
                    "filters": {"unsupported": "value"},
                    "keywords": [],
                    "ambiguities": [],
                    "unresolved": [],
                    "confidence": "low",
                }

        pipeline = QueryRetrievalPipeline(
            UnsafeUnderstanding(), self.pipeline.retriever
        )
        result = pipeline.run("unsafe")
        self.assertEqual(result["status"], "clarification_required")
        self.assertEqual(result["retrieval"]["records"], [])
        self.assertTrue(result["query_understanding"]["unresolved"])


if __name__ == "__main__":
    unittest.main()
