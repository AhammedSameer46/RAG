import copy
import json
import unittest

from cs_ingest.citation_builder import citation_handles
from cs_ingest.model_facing_context import build_model_facing_context


def _evidence(
    evidence_id,
    *,
    filename="source.pdf",
    page=1,
    text=None,
    raw_values=None,
    sheet=None,
    row=None,
    cell=None,
):
    value = {
        "evidence_id": evidence_id,
        "source_id": "sha256:internal",
        "filename": filename,
        "extracted_text": (
            f"Evidence {evidence_id}." if text is None else text
        ),
    }
    if page is not None:
        value["page"] = page
    if raw_values is not None:
        value["raw_values"] = raw_values
    for key, item in {"sheet": sheet, "row": row, "cell": cell}.items():
        if item is not None:
            value[key] = item
    return value


def _response(
    supporting=None,
    independent=None,
    observations=None,
    conflicts=None,
    lifecycle=None,
    coverage=None,
):
    supporting = supporting or []
    independent = independent or []
    all_evidence = supporting + independent
    observations = observations or [
        {
            "observation_id": f"observation-{index}",
            "evidence_ids": [item["evidence_id"]],
            "preserve_separately": False,
        }
        for index, item in enumerate(all_evidence)
    ]
    plan = {
        "observations": observations,
        "conflict_groups": conflicts or [],
        "lifecycle_groups": lifecycle or [],
        "coverage": coverage or {"complete": True},
    }
    return {
        "status": "answerable",
        "answer_plan": plan,
        "answer_context": {
            "records": [],
            "supporting_evidence": supporting,
            "independent_evidence": independent,
        },
    }


class ModelFacingContextTests(unittest.TestCase):
    def test_normal_context_and_pdf_location(self):
        result = build_model_facing_context(
            _response(supporting=[_evidence("a")])
        )
        self.assertEqual(result["evidence"][0]["id"], "E1")
        self.assertEqual(result["evidence"][0]["location"], {"page": 1})
        self.assertEqual(result["answer_plan"]["observations"][0]["evidence_ids"], ["E1"])

    def test_multiple_observations_preserve_order(self):
        result = build_model_facing_context(
            _response(supporting=[_evidence("a"), _evidence("b")])
        )
        self.assertEqual(
            result["answer_plan"]["observations"],
            [
                {"evidence_ids": ["E1"], "preserve_separately": False},
                {"evidence_ids": ["E2"], "preserve_separately": False},
            ],
        )

    def test_conflict_group_uses_observation_indexes(self):
        response = _response(
            supporting=[_evidence("a"), _evidence("b")],
            conflicts=[
                {
                    "observation_ids": ["observation-0", "observation-1"],
                    "must_preserve_separately": True,
                }
            ],
        )
        group = build_model_facing_context(response)["answer_plan"]["conflict_groups"][0]
        self.assertEqual(group, {
            "observation_indexes": [0, 1],
            "must_preserve_separately": True,
        })

    def test_lifecycle_group_uses_observation_indexes(self):
        response = _response(
            supporting=[_evidence("a"), _evidence("b")],
            lifecycle=[
                {
                    "observation_ids": ["observation-0", "observation-1"],
                    "must_distinguish": True,
                }
            ],
        )
        group = build_model_facing_context(response)["answer_plan"]["lifecycle_groups"][0]
        self.assertEqual(group["observation_indexes"], [0, 1])

    def test_incomplete_and_selection_budget_coverage(self):
        result = build_model_facing_context(
            _response(
                supporting=[_evidence("a")],
                coverage={
                    "complete": False,
                    "truncated": True,
                    "excluded_evidence_ids": ["b"],
                },
            )
        )
        self.assertEqual(
            result["answer_plan"]["coverage"],
            {"complete": False, "reason": "selection_budget"},
        )

    def test_generic_incomplete_coverage(self):
        result = build_model_facing_context(
            _response(supporting=[_evidence("a")], coverage={"complete": False})
        )
        self.assertEqual(
            result["answer_plan"]["coverage"],
            {"complete": False, "reason": "incomplete"},
        )

    def test_mixed_roles_are_preserved(self):
        result = build_model_facing_context(
            _response(
                supporting=[_evidence("a")],
                independent=[_evidence("b")],
            )
        )
        self.assertEqual(
            [item["role"] for item in result["evidence"]],
            ["supporting", "independent"],
        )

    def test_single_role_is_omitted(self):
        result = build_model_facing_context(
            _response(supporting=[_evidence("a")])
        )
        self.assertNotIn("role", result["evidence"][0])

    def test_spreadsheet_location_and_raw_values(self):
        result = build_model_facing_context(
            _response(
                supporting=[
                    _evidence(
                        "a",
                        filename="attendance.xlsx",
                        page=None,
                        text="",
                        raw_values={"Name": "Person", "Status": "Present"},
                        sheet="Faculty Attendance",
                        row=2,
                        cell="B2",
                    )
                ]
            )
        )
        item = result["evidence"][0]
        self.assertEqual(
            item["location"],
            {"sheet": "Faculty Attendance", "row": 2, "cell": "B2"},
        )
        self.assertIn("raw_values", item)
        self.assertIn("Name: Person", item["text"])

    def test_empty_non_factual_context(self):
        response = {
            "status": "insufficient_evidence",
            "answer_plan": {
                "observations": [],
                "conflict_groups": [],
                "lifecycle_groups": [],
                "coverage": {"complete": False},
            },
            "answer_context": {
                "records": [],
                "supporting_evidence": [],
                "independent_evidence": [],
            },
        }
        self.assertEqual(
            build_model_facing_context(response),
            {
                "answer_plan": {
                    "observations": [],
                    "conflict_groups": [],
                    "lifecycle_groups": [],
                    "coverage": {"complete": False, "reason": "incomplete"},
                },
                "evidence": [],
            },
        )

    def test_invalid_observation_reference_raises(self):
        response = _response(
            supporting=[_evidence("a")],
            observations=[{
                "observation_id": "bad",
                "evidence_ids": ["missing"],
                "preserve_separately": False,
            }],
        )
        with self.assertRaises(ValueError):
            build_model_facing_context(response)

    def test_invalid_conflict_index_reference_raises(self):
        response = _response(
            supporting=[_evidence("a")],
            conflicts=[{
                "observation_ids": ["missing"],
                "must_preserve_separately": True,
            }],
        )
        with self.assertRaises(ValueError):
            build_model_facing_context(response)

    def test_invalid_lifecycle_index_reference_raises(self):
        response = _response(
            supporting=[_evidence("a")],
            lifecycle=[{
                "observation_ids": ["missing"],
                "must_distinguish": True,
            }],
        )
        with self.assertRaises(ValueError):
            build_model_facing_context(response)

    def test_duplicate_handle_mapping_is_deduplicated(self):
        evidence = _evidence("a")
        response = _response(supporting=[evidence, copy.deepcopy(evidence)])
        result = build_model_facing_context(response)
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(list(citation_handles(response)), ["E1"])

    def test_input_is_immutable(self):
        response = _response(supporting=[_evidence("a")])
        original = copy.deepcopy(response)
        build_model_facing_context(response)
        self.assertEqual(response, original)

    def test_repeated_output_is_deterministic(self):
        response = _response(
            supporting=[_evidence("b"), _evidence("a")]
        )
        first = json.dumps(build_model_facing_context(response), sort_keys=True)
        second = json.dumps(build_model_facing_context(response), sort_keys=True)
        self.assertEqual(first, second)

    def test_internal_and_sensitive_metadata_do_not_leak(self):
        evidence = _evidence("a")
        evidence.update({
            "password": "secret",
            "authorization": "Bearer token",
            "selector_scores": {"rank": 1},
            "provenance_refs": [{"source_id": "secret"}],
            "matched_fields": ["keyword"],
        })
        result = build_model_facing_context(_response(supporting=[evidence]))
        serialized = json.dumps(result)
        for value in ("sha256:internal", "secret", "Bearer token", "selector_scores"):
            self.assertNotIn(value, serialized)

    def test_evaluator_metadata_does_not_leak(self):
        response = _response(supporting=[_evidence("a")])
        response["answer_plan"]["evaluator"] = {"expected_answer": "hidden"}
        result = build_model_facing_context(response)
        serialized = json.dumps(result)
        self.assertNotIn("expected_answer", serialized)

    def test_citation_builder_handle_compatibility(self):
        response = _response(
            supporting=[_evidence("a")],
            independent=[_evidence("b")],
        )
        result = build_model_facing_context(response)
        self.assertEqual(
            [item["id"] for item in result["evidence"]],
            list(citation_handles(response)),
        )

    def test_missing_required_plan_raises(self):
        response = _response(supporting=[_evidence("a")])
        del response["answer_plan"]
        with self.assertRaises(ValueError):
            build_model_facing_context(response)

    def test_empty_evidence_text_raises(self):
        with self.assertRaises(ValueError):
            build_model_facing_context(
                _response(
                    supporting=[
                        _evidence("a", text="", raw_values=None)
                    ]
                )
            )
