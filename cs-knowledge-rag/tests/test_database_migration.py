from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "migrations" / "001_initial_schema.sql"


class DatabaseMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.normalized_sql = re.sub(r"\s+", " ", cls.sql).lower()

    def test_initial_migration_exists_and_is_sql(self):
        self.assertTrue(MIGRATION.is_file())
        self.assertTrue(MIGRATION.name.endswith(".sql"))

    def test_creates_only_expected_tables(self):
        tables = re.findall(r"create table\s+([a-z_]+)", self.normalized_sql)
        self.assertEqual(
            tables,
            ["source", "evidence", "record", "record_evidence", "date_mention"],
        )

    def test_preserves_logical_identifiers_and_constraints(self):
        self.assertIn("source_id text primary key", self.normalized_sql)
        self.assertIn("evidence_id text primary key", self.normalized_sql)
        self.assertIn("record_id text primary key", self.normalized_sql)
        self.assertIn("sha256 char(64) not null unique", self.normalized_sql)
        self.assertIn("primary key (record_id, evidence_id)", self.normalized_sql)

    def test_preserves_provenance_and_json_fields(self):
        for field in (
            "kind text not null",
            "page integer",
            "sheet text",
            "row_number integer",
            "cell text",
            "cell_range text",
            "extracted_text text",
            "raw_values jsonb",
            "header_context jsonb",
            "attributes jsonb not null",
            "normalized_iso date not null",
        ):
            self.assertIn(field, self.normalized_sql)

    def test_foreign_keys_and_targeted_indexes_are_declared(self):
        self.assertEqual(self.normalized_sql.count("references source (source_id)"), 1)
        self.assertEqual(self.normalized_sql.count("references record (record_id)"), 1)
        self.assertEqual(self.normalized_sql.count("references evidence (evidence_id)"), 2)
        for index_name in (
            "evidence_source_id_idx",
            "evidence_kind_sheet_row_idx",
            "evidence_sheet_cell_idx",
            "record_record_type_idx",
            "record_meeting_date_idx",
            "record_event_start_date_idx",
            "record_event_end_date_idx",
            "record_attendance_person_idx",
            "record_event_name_idx",
            "date_mention_normalized_iso_idx",
            "date_mention_normalized_iso_role_idx",
            "date_mention_role_normalized_iso_idx",
            "date_mention_evidence_id_idx",
        ):
            self.assertIn(f"create index {index_name}", self.normalized_sql)

    def test_migration_contains_no_sample_inserts_or_destructive_ddl(self):
        self.assertNotRegex(self.normalized_sql, r"\binsert\s+into\b")
        self.assertNotRegex(self.normalized_sql, r"\bdrop\s+(table|schema)\b")
        self.assertNotIn("pgvector", self.normalized_sql)


if __name__ == "__main__":
    unittest.main()
