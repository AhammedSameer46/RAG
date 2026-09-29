import json
import unittest
from pathlib import Path

from cs_ingest.normalize import normalize_ingestion


ROOT = Path(__file__).parents[1]
INPUT = json.loads((ROOT / "output" / "sample_ingestion.json").read_text(encoding="utf-8"))


class NormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = normalize_ingestion(INPUT)

    def test_source_identity_uses_sha256(self):
        source = self.data["sources"][0]
        self.assertEqual(source["source_id"], f"sha256:{source['sha256']}")

    def test_pdf_evidence_provenance(self):
        page = next(item for item in self.data["evidence_units"] if item["kind"] == "pdf_page")
        self.assertEqual(page["source_id"], "sha256:" + page["source_id"].split("sha256:", 1)[1].split(":", 1)[0])
        self.assertEqual(page["page"], 1)
        self.assertTrue(page["extracted_text"])

    def test_excel_row_and_attendance_cell_provenance(self):
        row = next(
            item
            for item in self.data["evidence_units"]
            if item["kind"] == "worksheet_row" and item["sheet"] == "Meeting Log" and item["row"] == 2
        )
        self.assertEqual(row["raw_values"]["B"], "Department Meeting")
        cell = next(
            item
            for item in self.data["evidence_units"]
            if item["kind"] == "worksheet_cell" and item["cell"] == "B2"
        )
        self.assertEqual(cell["raw_values"]["faculty"], "Dr. Reena Nair")
        self.assertEqual(cell["raw_values"]["meeting_header"], "18-Jul-2026 (Dept Mtg)")
        self.assertEqual(cell["raw_values"]["attendance_value"], "Present")

    def test_date_mentions_reference_evidence(self):
        mention = next(
            item
            for item in self.data["date_mentions"]
            if item["original_text"] == "18/07/2026" and item["date_role"] == "meeting_date"
        )
        self.assertEqual(mention["normalized_iso"], "2026-07-18")
        self.assertIn(mention["evidence_id"], {item["evidence_id"] for item in self.data["evidence_units"]})

    def test_meeting_event_and_attendance_records(self):
        meeting = next(item for item in self.data["records"] if item["record_type"] == "meeting")
        self.assertEqual(meeting["attributes"]["meeting_date"], "2026-07-18")
        event = next(item for item in self.data["records"] if item["record_type"] == "event")
        self.assertEqual(event["attributes"]["name"], "C-START Industry Interaction")
        attendance = next(item for item in self.data["records"] if item["record_type"] == "attendance")
        self.assertEqual(attendance["attributes"]["person"], "Dr. Reena Nair")
        self.assertEqual(attendance["attributes"]["status"], "Present")

    def test_conflicting_participant_observations_are_preserved(self):
        event = next(
            item
            for item in self.data["records"]
            if item["attributes"].get("name") == "C-START Industry Interaction"
        )
        statements = {
            item["source_statement"] for item in event["attributes"]["participant_observations"]
        }
        self.assertEqual(
            statements,
            {
                "45 third-year students attended",
                "45 students from the third and fourth year batches participated",
            },
        )

    def test_serialization_is_deterministic(self):
        first = json.dumps(self.data, indent=2, ensure_ascii=False, sort_keys=True)
        second = json.dumps(normalize_ingestion(INPUT), indent=2, ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
