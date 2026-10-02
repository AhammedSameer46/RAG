import json
from pathlib import Path
from unittest import TestCase

from cs_ingest.persist import load_normalized_dataset


class PersistInputTests(TestCase):
    def test_loads_normalized_fixture(self):
        path = Path(__file__).parents[1] / "output" / "sample_normalized.json"
        dataset = load_normalized_dataset(path)

        self.assertEqual(dataset["schema_version"], 1)
        self.assertEqual(len(dataset["sources"]), 5)
        self.assertEqual(len(dataset["evidence_units"]), 35)
        self.assertEqual(len(dataset["records"]), 24)
        self.assertEqual(len(dataset["date_mentions"]), 24)

    def test_rejects_missing_top_level_field(self):
        path = Path(self.id().replace(".", "_")).with_suffix(".json")
        try:
            path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required keys"):
                load_normalized_dataset(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_non_object_json(self):
        path = Path(self.id().replace(".", "_")).with_suffix(".json")
        try:
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be a JSON object"):
                load_normalized_dataset(path)
        finally:
            path.unlink(missing_ok=True)
