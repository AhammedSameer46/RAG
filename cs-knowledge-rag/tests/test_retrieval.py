import json
import unittest
from copy import deepcopy
from pathlib import Path

from cs_ingest.retrieval import Retriever


ROOT = Path(__file__).parents[1]


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = Retriever.from_json(ROOT / "output" / "sample_normalized.json")

    def test_date_query_expands_matching_records_and_evidence(self):
        result = self.retriever.query(date="2026-07-18")
        self.assertEqual(
            {record["record_type"] for record in result["records"]},
            {"meeting", "event", "attendance"},
        )
        self.assertTrue(result["has_evidence"])
        self.assertTrue(all("filename" in item for item in result["evidence_units"]))

    def test_attendance_person_and_date_filters(self):
        result = self.retriever.query(
            date="2026-07-18", record_type="attendance", person="Dr. Reena Nair"
        )
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["attributes"]["status"], "Present")
        evidence = result["evidence_units"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["cell"], "B2")

    def test_event_name_filter(self):
        result = self.retriever.query(
            record_type="event", event_name="C-START Industry Interaction"
        )
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["attributes"]["coordinator"], "Prof. Sarah Thomas")
        self.assertEqual(len(result["evidence_units"]), 3)

    def test_keyword_search_retrieves_lab_procurement_evidence(self):
        result = self.retriever.query(keyword="lab procurement")
        self.assertTrue(result["has_evidence"])
        self.assertTrue(
            any(
                "lab equipment procurement" in item.get("extracted_text", "").lower()
                or "procurement" in str(item.get("raw_values", {})).lower()
                for item in result["evidence_units"]
            )
        )

    def test_date_role_filter(self):
        result = self.retriever.query(date_role="rescheduled_date")
        self.assertTrue(result["has_evidence"])
        self.assertEqual(result["records"], [])
        self.assertTrue(
            any(
                item["evidence_id"].endswith(":pdf-page:1")
                for item in result["evidence_units"]
            )
        )

    def test_date_role_does_not_admit_record_by_shared_document_date(self):
        result = self.retriever.query(
            date="2026-07-25",
            date_role="rescheduled_date",
        )
        self.assertEqual(result["records"], [])
        self.assertTrue(result["matched_evidence_units"])

    def test_date_filter_ignores_unrelated_date_attributes(self):
        data = deepcopy(self.retriever.data)
        meeting = next(
            record for record in data["records"] if record["record_type"] == "meeting"
        )
        meeting["attributes"]["next_meeting_date"] = "2099-01-01"
        retriever = Retriever(data)
        result = retriever.query(date="2099-01-01", record_type="meeting")
        self.assertEqual(result["records"], [])

    def test_keyword_evidence_is_distinguished_from_record_support(self):
        result = self.retriever.query(keyword="lab procurement")
        record_support = result["supporting_evidence_units"]
        keyword_matches = result["matched_evidence_units"]
        self.assertTrue(any(item["kind"] == "worksheet_row" for item in record_support))
        self.assertTrue(any(item["kind"] == "pdf_page" for item in keyword_matches))
        self.assertFalse(
            any(
                item["kind"] == "pdf_page"
                and item["filename"] == "CS_Dept_Meeting_Minutes_18Jul2026.pdf"
                for item in record_support
            )
        )

    def test_no_evidence_returns_empty_result(self):
        result = self.retriever.query(
            date="2099-01-01", keyword="information that does not exist"
        )
        self.assertEqual(result["records"], [])
        self.assertEqual(result["evidence_units"], [])
        self.assertFalse(result["has_evidence"])

    def test_serialization_of_result_is_stable(self):
        result = self.retriever.query(
            date="2026-07-18", record_type="meeting"
        )
        first = json.dumps(result, sort_keys=True)
        second = json.dumps(self.retriever.query(date="2026-07-18", record_type="meeting"), sort_keys=True)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
