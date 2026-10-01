import json
import unittest
from copy import deepcopy

from cs_ingest.answer_plan import build_answer_plan


def _response(
    *,
    status="answerable",
    supporting=None,
    independent=None,
    records=None,
    coverage=None,
    metadata=None,
):
    selection = dict(metadata or {})
    if coverage is not None:
        selection["coverage"] = coverage
    return {
        "status": status,
        "answer_context": {
            "records": records or [],
            "supporting_evidence": supporting or [],
            "independent_evidence": independent or [],
        },
        "selection": selection,
    }


def _evidence(evidence_id, *, filename="source.pdf", page=1):
    return {
        "evidence_id": evidence_id,
        "source_id": f"source:{evidence_id}",
        "filename": filename,
        "page": page,
        "extracted_text": f"evidence {evidence_id}",
    }


def _record(record_id, evidence_ids, matched_fields=None):
    record = {
        "record_id": record_id,
        "record_type": "meeting",
        "evidence_refs": [{"evidence_id": item} for item in evidence_ids],
    }
    if matched_fields is not None:
        record["matched_fields"] = matched_fields
    return record


class AnswerPlanTests(unittest.TestCase):
    def test_normal_factual_answer_creates_evidence_referenced_observation(self):
        response = _response(
            supporting=[_evidence("a")],
            records=[_record("record-a", ["a"], ["date"])],
            coverage={"coverage_complete": True, "conflict_coverage_complete": True},
        )
        plan = build_answer_plan(response)
        self.assertEqual(plan["answerability"], "answerable")
        self.assertEqual(plan["observations"][0]["evidence_ids"], ["a"])
        self.assertEqual(plan["observations"][0]["matched_fields"], ["date"])
        self.assertEqual(plan["citation_requirements"]["allowed_evidence_ids"], ["a"])

    def test_conflict_members_remain_separate(self):
        response = _response(
            supporting=[_evidence("a"), _evidence("b")],
            records=[_record("record-a", ["a", "b"])],
            coverage={
                "coverage_complete": True,
                "conflict_coverage_complete": True,
                "conflict_groups": [{
                    "coverage_group_id": "conflict:1",
                    "evidence_ids": ["a", "b"],
                    "selected_evidence_ids": ["a", "b"],
                    "excluded_evidence_ids": [],
                    "complete": True,
                    "reason": "different observations",
                }],
            },
        )
        plan = build_answer_plan(response)
        group = plan["conflict_groups"][0]
        self.assertTrue(group["must_preserve_separately"])
        self.assertEqual(
            group["observation_ids"],
            ["record:record-a:evidence:a", "record:record-a:evidence:b"],
        )
        self.assertTrue(
            all(
                observation["preserve_separately"]
                for observation in plan["observations"]
            )
        )

    def test_lifecycle_group_is_explicit(self):
        response = _response(
            supporting=[_evidence("planning"), _evidence("completed")],
            records=[
                _record("record-planning", ["planning"]),
                _record("record-completed", ["completed"]),
            ],
            coverage={
                "coverage_complete": True,
                "conflict_coverage_complete": True,
                "coverage_groups": [],
                "lifecycle_groups": [{
                    "coverage_group_id": "coverage:lifecycle",
                    "evidence_ids": ["planning", "completed"],
                    "selected_evidence_ids": ["planning", "completed"],
                    "excluded_evidence_ids": [],
                    "complete": True,
                    "reason": "related lifecycle stages",
                }],
            },
        )
        plan = build_answer_plan(response)
        group = plan["lifecycle_groups"][0]
        self.assertTrue(group["must_distinguish"])
        self.assertEqual(
            group["observation_ids"],
            ["record:record-completed", "record:record-planning"],
        )

    def test_incomplete_group_is_preserved_without_synthetic_observation(self):
        response = _response(
            supporting=[_evidence("a")],
            records=[_record("record-a", ["a"])],
            coverage={
                "coverage_complete": False,
                "conflict_coverage_complete": False,
                "conflict_groups": [{
                    "coverage_group_id": "conflict:incomplete",
                    "evidence_ids": ["a", "missing"],
                    "selected_evidence_ids": ["a"],
                    "excluded_evidence_ids": ["missing"],
                    "complete": False,
                    "reason": "budget",
                }],
            },
            metadata={"truncated": True, "excluded_evidence_ids": ["missing"]},
        )
        plan = build_answer_plan(response)
        self.assertEqual(len(plan["observations"]), 1)
        self.assertFalse(plan["conflict_groups"][0]["complete"])
        self.assertEqual(
            plan["coverage"]["missing_groups"][0]["excluded_evidence_ids"],
            ["missing"],
        )

    def test_non_answerable_statuses_have_no_observations(self):
        for status in ("clarification_required", "insufficient_evidence"):
            plan = build_answer_plan(
                _response(
                    status=status,
                    supporting=[_evidence("should-not-be-used")],
                    records=[_record("record", ["should-not-be-used"])],
                )
            )
            self.assertEqual(plan["observations"], [])
            self.assertEqual(plan["citation_requirements"]["allowed_evidence_ids"], [])

    def test_supporting_and_independent_roles_are_distinct(self):
        response = _response(
            supporting=[_evidence("support")],
            independent=[_evidence("independent")],
            records=[_record("record", ["support", "independent"])],
            coverage={"coverage_complete": True},
        )
        plan = build_answer_plan(response)
        self.assertEqual(
            plan["observations"][0]["roles"],
            {"supporting": ["support"], "independent": ["independent"]},
        )

    def test_provenance_is_preserved_as_references(self):
        response = _response(
            supporting=[_evidence("a", filename="minutes.pdf", page=3)],
            records=[_record("record-a", ["a"])],
        )
        provenance = build_answer_plan(response)["observations"][0]["provenance_refs"]
        self.assertEqual(provenance[0]["filename"], "minutes.pdf")
        self.assertEqual(provenance[0]["page"], 3)
        self.assertEqual(provenance[0]["evidence_id"], "a")

    def test_repeated_calls_are_deterministic(self):
        response = _response(
            supporting=[_evidence("b"), _evidence("a")],
            records=[_record("record", ["b", "a"])],
            coverage={"coverage_complete": True},
        )
        first = json.dumps(build_answer_plan(response), sort_keys=True, separators=(",", ":"))
        second = json.dumps(build_answer_plan(response), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)

    def test_input_is_not_mutated(self):
        response = _response(
            supporting=[_evidence("a")],
            records=[_record("record-a", ["a"])],
            coverage={"coverage_complete": True},
        )
        original = deepcopy(response)
        build_answer_plan(response)
        self.assertEqual(response, original)

    def test_malformed_optional_groups_are_ignored_without_inventing_data(self):
        response = _response(
            supporting=[_evidence("a")],
            records=[_record("record-a", ["a"])],
            coverage={"coverage_complete": True, "conflict_groups": ["bad"]},
        )
        plan = build_answer_plan(response)
        self.assertEqual(plan["conflict_groups"], [])
        self.assertEqual(plan["observations"][0]["evidence_ids"], ["a"])


if __name__ == "__main__":
    unittest.main()
