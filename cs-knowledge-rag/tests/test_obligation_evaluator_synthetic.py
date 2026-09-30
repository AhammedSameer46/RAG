import json
import unittest
from copy import deepcopy
from pathlib import Path

from evaluation.obligation_evaluator import evaluate_obligations


ROOT = Path(__file__).parents[1]
with (ROOT / "evaluation" / "ANSWER_OBLIGATIONS.json").open(
    encoding="utf-8"
) as stream:
    OBLIGATIONS = {
        item["id"]: item for item in json.load(stream)["obligations"]
    }

EVIDENCE = [
    {
        "evidence_id": "event-report",
        "filename": "CSTART_2026_Event_Report.pdf",
        "page": 1,
    },
    {
        "evidence_id": "meeting-minutes",
        "filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf",
        "page": 1,
    },
    {
        "evidence_id": "events-row",
        "filename": "CS_Meetings_Events_Log.xlsx",
        "sheet": "Events",
        "row": 2,
    },
    {
        "evidence_id": "completed-event",
        "filename": "CS_Meetings_Events_Log.xlsx",
        "sheet": "Events",
        "row": 3,
    },
    {
        "evidence_id": "planning-meeting",
        "filename": "CS_Meetings_Events_Log.xlsx",
        "sheet": "Meeting Log",
        "row": 5,
    },
]
HANDLES = {f"E{index}": item["evidence_id"] for index, item in enumerate(EVIDENCE, 1)}


class SyntheticObligationEvaluatorTests(unittest.TestCase):
    def evaluate(self, case_id, claims, mapping=None, evidence=None):
        obligation = OBLIGATIONS[case_id]
        return evaluate_obligations(
            obligation["question"],
            obligation,
            {"status": "answered", "claims": claims},
            mapping or HANDLES,
            evidence or EVIDENCE,
        )

    def test_e006_direct_event_report_citation_passes(self):
        result = self.evaluate(
            "E006",
            [
                {
                    "text": "Prof. Sarah Thomas coordinated C-START.",
                    "citation_refs": ["E1"],
                }
            ],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["wrong_citation_obligations"], [])

    def test_e006_meeting_minutes_only_is_wrong_citation(self):
        result = self.evaluate(
            "E006",
            [
                {
                    "text": "Prof. Sarah Thomas coordinated C-START.",
                    "citation_refs": ["E2"],
                }
            ],
        )
        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn("coordinator", result["wrong_citation_obligations"])
        self.assertEqual(result["missing_obligations"], [])

    def test_e014_both_participant_observations_pass(self):
        result = self.evaluate(
            "E014",
            [
                {
                    "text": "The event report states that 45 third and fourth year students participated.",
                    "citation_refs": ["E1"],
                },
                {
                    "text": "The meeting minutes state that 45 third-year students attended.",
                    "citation_refs": ["E2"],
                },
            ],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["conflict_preservation"][0]["complete"])

    def test_e014_one_or_collapsed_observation_fails(self):
        one = self.evaluate(
            "E014",
            [
                {
                    "text": "45 third and fourth year students participated.",
                    "citation_refs": ["E1"],
                }
            ],
        )
        collapsed = self.evaluate(
            "E014",
            [{"text": "45 students participated.", "citation_refs": ["E1"]}],
        )
        self.assertEqual(one["status"], "PARTIAL")
        self.assertIn("cstart_participant_category", one["missing_obligations"])
        self.assertEqual(collapsed["status"], "PARTIAL")
        self.assertIn("cstart_participant_category", collapsed["missing_obligations"])

    def test_e016_both_lifecycle_observations_pass(self):
        result = self.evaluate(
            "E016",
            [
                {
                    "text": "The FDP Planning meeting occurred on 10 August 2026.",
                    "citation_refs": ["E5"],
                },
                {
                    "text": "The FDP event was recorded as Completed for 10–14 August 2026.",
                    "citation_refs": ["E4"],
                },
            ],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["lifecycle_distinction"][0]["complete"])

    def test_e016_single_lifecycle_observation_fails(self):
        for claims, missing in (
            (
                [
                    {
                        "text": "The FDP Planning meeting occurred on 10 August 2026.",
                        "citation_refs": ["E5"],
                    }
                ],
                "completed_event",
            ),
            (
                [
                    {
                        "text": "The FDP event was recorded as Completed for 10–14 August 2026.",
                        "citation_refs": ["E4"],
                    }
                ],
                "planning_meeting",
            ),
        ):
            with self.subTest(missing=missing):
                result = self.evaluate("E016", claims)
                self.assertEqual(result["status"], "PARTIAL")
                self.assertIn(missing, result["missing_obligations"])

    def test_e017_count_and_both_categories_pass(self):
        result = self.evaluate(
            "E017",
            [
                {
                    "text": "The reported count was 45 participants.",
                    "citation_refs": ["E1"],
                },
                {
                    "text": "The event report described 45 third and fourth year students.",
                    "citation_refs": ["E1"],
                },
                {
                    "text": "The meeting minutes described 45 third-year students.",
                    "citation_refs": ["E2"],
                },
            ],
        )
        self.assertEqual(result["status"], "PASS")

    def test_e017_count_only_or_one_category_is_incomplete(self):
        count_only = self.evaluate(
            "E017",
            [{"text": "The reported count was 45 participants.", "citation_refs": ["E1"]}],
        )
        one_category = self.evaluate(
            "E017",
            [
                {
                    "text": "The reported count was 45 third and fourth year students.",
                    "citation_refs": ["E1"],
                }
            ],
        )
        self.assertEqual(count_only["status"], "PARTIAL")
        self.assertIn("participant_category_discrepancy", count_only["missing_obligations"])
        self.assertEqual(one_category["status"], "PARTIAL")
        self.assertIn("participant_category_discrepancy", one_category["missing_obligations"])

    def test_invalid_handle_is_failure(self):
        result = self.evaluate(
            "E006",
            [
                {
                    "text": "Prof. Sarah Thomas coordinated C-START.",
                    "citation_refs": ["E9"],
                }
            ],
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["invalid_evidence_handles"], ["E9"])

    def test_no_false_pass_from_superficial_overlap(self):
        result = self.evaluate(
            "E014",
            [
                {
                    "text": "45 third and fourth year students participated.",
                    "citation_refs": ["E2"],
                },
                {
                    "text": "45 third-year students attended.",
                    "citation_refs": ["E1"],
                },
            ],
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("cstart_participant_category", result["missing_obligations"])
        observations = result["conflict_preservation"][0]["observations"]
        self.assertTrue(all(item["wrong_citation"] for item in observations))

    def test_input_immutability_and_determinism(self):
        claims = [
            {
                "text": "The reported count was 45 participants.",
                "citation_refs": ["E1"],
            }
        ]
        obligation = deepcopy(OBLIGATIONS["E017"])
        mapping = deepcopy(HANDLES)
        evidence = deepcopy(EVIDENCE)
        before = deepcopy((obligation, claims, mapping, evidence))
        first = self.evaluate("E017", claims, mapping, evidence)
        second = self.evaluate("E017", claims, mapping, evidence)
        self.assertEqual(first, second)
        self.assertEqual((obligation, claims, mapping, evidence), before)
