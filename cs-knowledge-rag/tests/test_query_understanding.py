import unittest
from pathlib import Path

from cs_ingest.query_understanding import QueryUnderstanding


ROOT = Path(__file__).parents[1]


class QueryUnderstandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = QueryUnderstanding.from_json(ROOT / "output" / "sample_normalized.json")

    def test_date_activity(self):
        result = self.parser.understand("What happened on 18 July 2026?")
        self.assertEqual(result["intent"], "date_activity")
        self.assertEqual(result["retrieval_mode"], "exact")
        self.assertEqual(result["filters"]["date"], "2026-07-18")

    def test_attendance_with_unsupported_meeting_type(self):
        result = self.parser.understand(
            "Was Dr. Reena Nair present at the department meeting on 18 July 2026?"
        )
        self.assertEqual(result["intent"], "attendance_lookup")
        self.assertEqual(result["filters"]["record_type"], "attendance")
        self.assertEqual(result["filters"]["person"], "Dr. Reena Nair")
        self.assertEqual(result["filters"]["date"], "2026-07-18")
        self.assertTrue(any("meeting type" in item for item in result["unresolved"]))

    def test_date_role_lookup(self):
        result = self.parser.understand("When was the faculty meeting rescheduled?")
        self.assertEqual(result["intent"], "date_role_lookup")
        self.assertEqual(result["filters"]["date_role"], "rescheduled_date")
        self.assertEqual(result["filters"]["keyword"], "faculty meeting")
        self.assertEqual(result["retrieval_mode"], "exact_and_keyword")

    def test_cstart_remains_conservative(self):
        result = self.parser.understand("Who coordinated C-START?")
        self.assertEqual(result["intent"], "event_lookup")
        self.assertNotIn("event_name", result["filters"])
        self.assertIn("C-START", result["keywords"])

    def test_narrative_keywords(self):
        result = self.parser.understand("What was discussed about lab procurement?")
        self.assertEqual(result["intent"], "narrative_search")
        self.assertEqual(result["retrieval_mode"], "keyword")
        self.assertEqual(set(result["keywords"]), {"lab", "procurement"})

    def test_fdp_decision_does_not_require_decision_keyword(self):
        result = self.parser.understand("What decisions were made regarding the FDP?")
        self.assertIn(result["intent"], {"narrative_search", "mixed_query"})
        self.assertIn("FDP", result["keywords"])
        self.assertNotIn("decision", result["keywords"])

    def test_person_activity_has_coverage_limit(self):
        result = self.parser.understand("Which meetings did Prof. Sarah Thomas attend?")
        self.assertEqual(result["intent"], "person_activity")
        self.assertEqual(result["filters"]["record_type"], "attendance")
        self.assertEqual(result["filters"]["person"], "Prof. Sarah Thomas")
        self.assertTrue(result["unresolved"])

    def test_mixed_date_and_fdp(self):
        result = self.parser.understand("What happened on 10 August 2026 regarding the FDP?")
        self.assertEqual(result["intent"], "mixed_query")
        self.assertEqual(result["filters"]["date"], "2026-08-10")
        self.assertIn("FDP", result["keywords"])
        self.assertEqual(result["retrieval_mode"], "exact_and_keyword")

    def test_event_attendee_list_limit(self):
        result = self.parser.understand("Who attended the C-START event?")
        self.assertEqual(result["intent"], "event_lookup")
        self.assertTrue(any("complete event attendee list" in item for item in result["unresolved"]))

    def test_broad_question_is_unknown(self):
        result = self.parser.understand("Tell me something about the department.")
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["confidence"], "low")
        self.assertTrue(result["ambiguities"])
        self.assertTrue(result["unresolved"])

    def test_negative_cases_do_not_guess(self):
        missing_year = self.parser.understand("What happened on 18 July?")
        self.assertNotIn("date", missing_year["filters"])
        self.assertTrue(missing_year["unresolved"])
        incomplete_person = self.parser.understand("Was Reena present?")
        self.assertNotIn("person", incomplete_person["filters"])
        self.assertTrue(incomplete_person["unresolved"])
        ambiguous_role = self.parser.understand("When was the meeting?")
        self.assertNotIn("date_role", ambiguous_role["filters"])
        self.assertTrue(ambiguous_role["unresolved"])

    def test_date_formats_and_unsupported_range(self):
        for question in ("on 18/07/2026", "on 18-Jul-2026"):
            self.assertEqual(
                self.parser.understand(question)["filters"]["date"], "2026-07-18"
            )
        result = self.parser.understand("What happened during July 2026?")
        self.assertNotIn("date", result["filters"])
        self.assertTrue(any("Date-range" in item for item in result["unresolved"]))

    def test_unknown_person_and_event_are_not_fabricated(self):
        person = self.parser.understand("Was Dr. Unknown Person present?")
        self.assertEqual(person["filters"]["person"], "Dr. Unknown Person")
        self.assertTrue(person["unresolved"])
        event = self.parser.understand("Who coordinated the industry event?")
        self.assertNotIn("event_name", event["filters"])
        self.assertTrue(event["unresolved"] or event["keywords"])


if __name__ == "__main__":
    unittest.main()
