import hashlib
import unittest
from pathlib import Path

from cs_ingest.ingest import ingest_directory


ROOT = Path(__file__).parents[1]
SAMPLE_DATA = ROOT.parent / "sample_data"


class IngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = ingest_directory(SAMPLE_DATA)

    def test_discovers_all_five_files_and_hashes_them(self):
        self.assertEqual(len(self.data["sources"]), 5)
        for source in self.data["sources"]:
            self.assertEqual(len(source["sha256"]), 64)
        expected = hashlib.sha256(
            (SAMPLE_DATA / "CS_Dept_Meeting_Minutes_18Jul2026.pdf").read_bytes()
        ).hexdigest()
        source = next(
            item
            for item in self.data["sources"]
            if item["filename"] == "CS_Dept_Meeting_Minutes_18Jul2026.pdf"
        )
        self.assertEqual(source["sha256"], expected)

    def test_pdf_pages_have_provenance_and_text(self):
        self.assertEqual(len(self.data["pdf_pages"]), 3)
        for page in self.data["pdf_pages"]:
            self.assertEqual(page["page_number"], 1)
            self.assertTrue(page["text"].strip())
            self.assertEqual(page["provenance"]["page"], 1)

    def test_workbook_sheets_and_row_provenance(self):
        names = {(item["source"], item["sheet_name"]) for item in self.data["worksheets"]}
        self.assertIn(("CS_Meetings_Events_Log.xlsx", "Meeting Log"), names)
        self.assertIn(("CS_Meetings_Events_Log.xlsx", "Events"), names)
        self.assertIn(("CS_Faculty_Attendance_GoogleSheet.xlsx", "Faculty Attendance"), names)
        attendance = next(
            item for item in self.data["worksheets"] if item["sheet_name"] == "Faculty Attendance"
        )
        self.assertEqual(attendance["rows"][1]["values"]["B"], "Present")
        self.assertEqual(attendance["rows"][1]["header_context"]["B"], "18-Jul-2026 (Dept Mtg)")
        self.assertEqual(attendance["rows"][1]["provenance"]["row"], 2)

    def test_dates_are_normalized_and_roles_are_retained(self):
        dates = {(item["original_text"], item["normalized_iso"], item["date_role"]) for item in self.data["dates"]}
        self.assertIn(("18/07/2026", "2026-07-18", "meeting_date"), dates)
        self.assertIn(("20 July 2026", "2026-07-20", "original_date"), dates)
        self.assertIn(("25 July 2026", "2026-07-25", "rescheduled_date"), dates)
        self.assertIn(("10-Aug-2026", "2026-08-10", "start_date"), dates)


if __name__ == "__main__":
    unittest.main()
