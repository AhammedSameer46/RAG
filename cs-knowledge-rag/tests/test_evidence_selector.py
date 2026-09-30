import unittest
from copy import deepcopy
import json
from pathlib import Path

from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class EvidenceSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline = QueryRetrievalPipeline.from_json(ROOT / "output" / "sample_normalized.json")
        cls.response = build_evidence_response(pipeline.run("What happened on 18 July 2026?"))
        cls.selector = EvidenceSelector()
        cls.query = cls.response["query_understanding"]

    def select(self, response=None, config=None):
        if isinstance(response, EvidenceSelectionConfig):
            config, response = response, None
        return self.selector.select(
            "What happened on 18 July 2026?",
            self.query,
            response or self.response,
            config or EvidenceSelectionConfig(max_evidence_units=20, max_characters=100000),
        )

    def test_deterministic_ordering(self):
        first = self.select()
        second = self.select()
        self.assertEqual(first, second)

    def test_relevance_and_provenance_are_preserved(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=2, max_characters=100000))
        units = result["selected_supporting_evidence"]
        self.assertTrue(units)
        self.assertTrue(all("evidence_id" in unit and "source_id" in unit for unit in units))

    def test_supporting_priority_over_independent(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=1, max_characters=100000))
        supporting_ids = {
            unit["evidence_id"]
            for unit in self.response["answer_context"]["supporting_evidence"]
        }
        self.assertIn(result["selected_supporting_evidence"][0]["evidence_id"], supporting_ids)
        self.assertEqual(result["selected_independent_evidence"], [])

    def test_unit_budget_and_exclusions(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=2, max_characters=100000))
        self.assertEqual(result["selection_metadata"]["selected_count"], 2)
        self.assertTrue(result["selection_metadata"]["excluded_evidence"])
        self.assertTrue(result["selection_metadata"]["truncated"])

    def test_character_budget(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=20, max_characters=10))
        self.assertTrue(result["selection_metadata"]["truncated"])
        self.assertTrue(result["selection_metadata"]["excluded_evidence"])

    def test_character_budget_includes_records_and_matches_context(self):
        config = EvidenceSelectionConfig(max_evidence_units=1, max_characters=100000)
        result = self.select(config)
        context = {
            "records": result["selected_records"],
            "supporting_evidence": result["selected_supporting_evidence"],
            "independent_evidence": result["selected_independent_evidence"],
        }
        expected = len(json.dumps(context, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
        self.assertEqual(result["selection_metadata"]["characters_used"], expected)
        self.assertGreater(
            expected,
            sum(
                len(json.dumps(unit, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
                for unit in result["selected_supporting_evidence"]
            ),
        )

    def test_exact_character_limit_is_accepted_and_one_over_is_rejected(self):
        unconstrained = self.select(
            EvidenceSelectionConfig(max_evidence_units=1, max_characters=100000)
        )
        exact_context = {
            "records": unconstrained["selected_records"],
            "supporting_evidence": unconstrained["selected_supporting_evidence"],
            "independent_evidence": unconstrained["selected_independent_evidence"],
        }
        exact = unconstrained["selection_metadata"]["characters_used"]
        accepted = self.select(
            EvidenceSelectionConfig(max_evidence_units=1, max_characters=exact)
        )
        rejected = self.select(
            EvidenceSelectionConfig(max_evidence_units=1, max_characters=exact - 1)
        )
        self.assertEqual(accepted["selection_metadata"]["characters_used"], exact)
        self.assertEqual(
            accepted["selection_metadata"]["characters_used"],
            len(json.dumps(exact_context, sort_keys=True, ensure_ascii=False, separators=(",", ":"))),
        )
        self.assertLess(rejected["selection_metadata"]["characters_used"], exact)
        self.assertTrue(rejected["selection_metadata"]["truncated"])

    def test_record_budget(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=20, max_characters=100000, max_records=1))
        self.assertEqual(len(result["selected_records"]), 1)
        self.assertTrue(
            any(
                item["reason"] == "max_records"
                for item in result["selection_metadata"]["excluded_evidence"]
            )
        )

    def test_duplicate_ids_are_deduplicated(self):
        response = deepcopy(self.response)
        unit = response["answer_context"]["supporting_evidence"][0]
        response["answer_context"]["supporting_evidence"].append(deepcopy(unit))
        result = self.select(response)
        ids = [u["evidence_id"] for u in result["selected_supporting_evidence"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_conflicting_duplicate_text_fails(self):
        response = deepcopy(self.response)
        unit = response["answer_context"]["supporting_evidence"][0]
        duplicate = deepcopy(unit)
        duplicate["extracted_text"] = "different"
        response["answer_context"]["supporting_evidence"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate evidence_id"):
            self.select(response)

    def test_conflicting_duplicate_source_fails(self):
        response = deepcopy(self.response)
        unit = response["answer_context"]["supporting_evidence"][0]
        duplicate = deepcopy(unit)
        duplicate["source_id"] = "different-source"
        response["answer_context"]["supporting_evidence"].append(duplicate)
        with self.assertRaises(ValueError):
            self.select(response)

    def test_conflicting_duplicate_location_fails(self):
        response = deepcopy(self.response)
        unit = response["answer_context"]["supporting_evidence"][0]
        duplicate = deepcopy(unit)
        duplicate["page"] = 99
        response["answer_context"]["supporting_evidence"].append(duplicate)
        with self.assertRaises(ValueError):
            self.select(response)

    def test_conflicting_duplicate_across_roles_fails(self):
        response = deepcopy(self.response)
        unit = response["answer_context"]["supporting_evidence"][0]
        duplicate = deepcopy(unit)
        duplicate["extracted_text"] = "different"
        response["answer_context"]["independent_evidence"].append(duplicate)
        with self.assertRaises(ValueError):
            self.select(response)

    def test_participant_conflict_is_selected_as_a_group(self):
        result = self.select(
            EvidenceSelectionConfig(max_evidence_units=2, max_characters=100000)
        )
        groups = result["selection_metadata"]["coverage"]["conflict_groups"]
        self.assertTrue(groups)
        group = groups[0]
        self.assertTrue(group["complete"])
        self.assertEqual(
            set(group["evidence_ids"]),
            set(group["selected_evidence_ids"]),
        )

    def test_conflict_budget_exhaustion_is_explicit(self):
        result = self.select(
            EvidenceSelectionConfig(max_evidence_units=1, max_characters=100000)
        )
        groups = result["selection_metadata"]["coverage"]["conflict_groups"]
        self.assertTrue(groups)
        self.assertFalse(groups[0]["complete"])
        self.assertLessEqual(
            result["selection_metadata"]["selected_count"], 1
        )

    def test_date_activity_prioritizes_distinct_record_types(self):
        result = self.select(
            EvidenceSelectionConfig(max_evidence_units=5, max_characters=100000)
        )
        selected_types = {
            record["record_type"] for record in result["selected_records"]
        }
        self.assertTrue({"meeting", "event", "attendance"} <= selected_types)

    def test_lifecycle_group_preserves_planning_and_completed_records(self):
        pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        response = build_evidence_response(
            pipeline.run("What happened on 10 August 2026?")
        )
        query = response["query_understanding"]
        result = self.selector.select(
            "What happened on 10 August 2026?",
            query,
            response,
            EvidenceSelectionConfig(max_evidence_units=3, max_characters=100000),
        )
        groups = result["selection_metadata"]["coverage"]["coverage_groups"]
        self.assertTrue(any(group["kind"] == "lifecycle" and group["complete"] for group in groups))

    def test_supporting_tier_beats_independent_specificity(self):
        response = {
            "status": "answerable",
            "answer_context": {
                "records": [],
                "supporting_evidence": [
                    {
                        "evidence_id": "supporting",
                        "source_id": "source",
                        "filename": "file",
                        "extracted_text": "supported fact",
                    }
                ],
                "independent_evidence": [
                    {
                        "evidence_id": "independent",
                        "source_id": "source",
                        "filename": "file",
                        "page": 1,
                        "cell": "A1",
                        "extracted_text": "unrelated fact",
                    }
                ],
            },
        }
        result = self.select(
            response,
            EvidenceSelectionConfig(max_evidence_units=1, max_characters=10000),
        )
        self.assertEqual(
            result["selected_supporting_evidence"][0]["evidence_id"], "supporting"
        )
        self.assertEqual(result["selected_independent_evidence"], [])

    def test_selected_evidence_never_orphans_required_record(self):
        response = deepcopy(self.response)
        result = self.select(
            response,
            EvidenceSelectionConfig(
                max_evidence_units=3, max_characters=100000, max_records=0
            ),
        )
        self.assertEqual(result["selected_supporting_evidence"], [])
        self.assertEqual(result["selected_independent_evidence"], [])
        self.assertTrue(result["selection_metadata"]["excluded_evidence"])

    def test_input_is_immutable(self):
        snapshot = deepcopy(self.response)
        self.select()
        self.assertEqual(self.response, snapshot)

    def test_conflict_flag_is_detected(self):
        result = self.select()
        self.assertTrue(result["selection_metadata"]["conflict_flags"])
        self.assertEqual(result["selection_metadata"]["conflict_flags"][0]["dimension"], "participant_category")

    def test_conflict_coverage_is_reported(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=1, max_characters=100000))
        self.assertIn("conflict_coverage_complete", result["selection_metadata"]["coverage"])

    def test_oversized_unit_is_excluded(self):
        result = self.select(EvidenceSelectionConfig(max_evidence_units=20, max_characters=100000, max_characters_per_unit=1))
        self.assertTrue(result["selection_metadata"]["excluded_evidence"])
        self.assertTrue(all(item["reason"] == "max_characters_per_unit" for item in result["selection_metadata"]["excluded_evidence"]))

    def test_non_answerable_status_has_empty_selection(self):
        response = deepcopy(self.response)
        response["status"] = "insufficient_evidence"
        result = self.select(response)
        self.assertEqual(result["selected_records"], [])
        self.assertEqual(result["selected_supporting_evidence"], [])
        self.assertEqual(result["selected_independent_evidence"], [])

    def test_exact_locations_survive(self):
        result = self.select()
        original = {u["evidence_id"]: u for u in self.response["answer_context"]["supporting_evidence"]}
        for unit in result["selected_supporting_evidence"]:
            self.assertEqual(unit, original[unit["evidence_id"]])


if __name__ == "__main__":
    unittest.main()
