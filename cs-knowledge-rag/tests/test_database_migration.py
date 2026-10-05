from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
MIGRATIONS = ROOT / "migrations"


def _normalized(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).lower()


class DatabaseMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial_sql = _normalized(MIGRATIONS / "001_initial_schema.sql")
        cls.drive_sql = _normalized(MIGRATIONS / "002_drive_sync.sql")

    def test_initial_migration_exists_and_contains_only_original_tables(self):
        migration = MIGRATIONS / "001_initial_schema.sql"
        self.assertTrue(migration.is_file())
        self.assertEqual(
            re.findall(r"create table\s+([a-z_]+)", self.initial_sql),
            ["source", "evidence", "record", "record_evidence", "date_mention"],
        )
        self.assertNotIn("drive_sync_run", self.initial_sql)
        self.assertNotIn("drive_file", self.initial_sql)

    def test_initial_migration_preserves_original_contract(self):
        for fragment in (
            "source_id text primary key",
            "evidence_id text primary key",
            "record_id text primary key",
            "sha256 char(64) not null unique",
            "primary key (record_id, evidence_id)",
            "evidence_source_id_idx",
            "date_mention_evidence_id_idx",
        ):
            self.assertIn(fragment, self.initial_sql)

    def test_drive_migration_contains_only_drive_tables(self):
        self.assertEqual(
            re.findall(r"create table\s+([a-z_]+)", self.drive_sql),
            ["drive_sync_run", "drive_file"],
        )
        self.assertNotIn("create table source", self.drive_sql)
        self.assertNotIn("create table evidence", self.drive_sql)
        self.assertNotIn("create table record", self.drive_sql)
        self.assertNotIn("create table date_mention", self.drive_sql)

    def test_drive_schema_fields_constraints_and_indexes(self):
        for fragment in (
            "sync_run_id text primary key",
            "root_folder_id text not null",
            "started_at timestamptz not null",
            "completed_at timestamptz",
            "status text not null",
            "status in ('running', 'succeeded', 'failed')",
            "drive_file_id text primary key",
            "source_id text references source (source_id)",
            "parent_ids jsonb not null",
            "jsonb_typeof(parent_ids) = 'array'",
            "modified_time timestamptz",
            "indexed_modified_time timestamptz",
            "last_seen_run_id text references drive_sync_run (sync_run_id)",
            "last_seen_at timestamptz not null",
            "last_indexed_at timestamptz",
            "drive_file_root_folder_id_idx",
            "drive_file_last_seen_run_id_idx",
        ):
            self.assertIn(fragment, self.drive_sql)
        self.assertNotIn("source_id text not null unique", self.drive_sql)

    def test_migrations_contain_no_sample_inserts_or_destructive_ddl(self):
        for sql in (self.initial_sql, self.drive_sql):
            self.assertNotRegex(sql, r"\binsert\s+into\b")
            self.assertNotRegex(sql, r"\bdrop\s+(table|schema)\b")
            self.assertNotIn("pgvector", sql)


if __name__ == "__main__":
    unittest.main()
