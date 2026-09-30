import unittest
from copy import deepcopy

from evaluation.obligation_evaluator import evaluate_obligations


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
]


def obligation(**changes):
    value = {
        "question": "Q",
        "required_observations": [
            {
                "id": "fact",
                "all_phrases": ["Sarah Thomas"],
                "required_evidence": [
                    {
                        "filename": "CSTART_2026_Event_Report.pdf",
                        "location": {"page": 1},
                    }
                ],
            }
        ],
        "required_evidence_relationships": [],
        "conflict_requirements": [],
        "lifecycle_requirements": [],
        "direct_citation_requirements": [],
    }
    value.update(changes)
    return value


class ObligationEvaluatorTests(unittest.TestCase):
    def evaluate(self, spec, claims, mapping=None, evidence=None):
        return evaluate_obligations(
            "Q",
            spec,
            {"status": "answered", "claims": claims},
            mapping or {"E1": "event-report", "E2": "meeting-minutes"},
            evidence or EVIDENCE,
        )

    def test_fully_satisfied_obligation(self):
        result = self.evaluate(
            obligation(),
            [{"text": "Sarah Thomas coordinated C-START.", "citation_refs": ["E1"]}],
        )
        self.assertEqual(result["status"], "PASS")

    def test_missing_claim(self):
        result = self.evaluate(obligation(), [])
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("fact", result["missing_obligations"])

    def test_wrong_citation(self):
        result = self.evaluate(
            obligation(),
            [{"text": "Sarah Thomas coordinated C-START.", "citation_refs": ["E2"]}],
        )
        self.assertIn("fact", result["wrong_citation_obligations"])

    def test_conflict_preserved_and_collapsed(self):
        spec = obligation(
            required_observations=[],
            conflict_requirements=[{
                "id": "participants",
                "observations": [
                    {"id": "event", "all_phrases": ["45", "third", "fourth"], "required_evidence": [{"filename": "CSTART_2026_Event_Report.pdf", "location": {"page": 1}}]},
                    {"id": "meeting", "all_phrases": ["45", "third-year"], "required_evidence": [{"filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf", "location": {"page": 1}}]},
                ],
            }],
        )
        passed = self.evaluate(spec, [
            {"text": "45 third and fourth year students participated.", "citation_refs": ["E1"]},
            {"text": "45 third-year students attended.", "citation_refs": ["E2"]},
        ])
        collapsed = self.evaluate(spec, [
            {"text": "45 students participated.", "citation_refs": ["E1"]},
        ])
        self.assertTrue(passed["conflict_preservation"][0]["complete"])
        self.assertFalse(collapsed["conflict_preservation"][0]["complete"])

    def test_lifecycle_preserved_and_missing(self):
        spec = obligation(
            required_observations=[],
            lifecycle_requirements=[{
                "id": "lifecycle",
                "observations": [
                    {"id": "planning", "all_phrases": ["planning"], "required_evidence": [{"filename": "CS_Dept_Meeting_Minutes_18Jul2026.pdf", "location": {"page": 1}}]},
                    {"id": "completed", "all_phrases": ["completed"], "required_evidence": [{"filename": "CSTART_2026_Event_Report.pdf", "location": {"page": 1}}]},
                ],
            }],
        )
        result = self.evaluate(spec, [
            {"text": "A planning meeting was held.", "citation_refs": ["E2"]},
            {"text": "The event was completed.", "citation_refs": ["E1"]},
        ])
        self.assertTrue(result["lifecycle_distinction"][0]["complete"])

    def test_acceptable_omission_is_reported(self):
        spec = obligation(
            required_observations=[],
            acceptable_scope=["Attendance details may be omitted."],
            incomplete_conditions=["Missing the event."],
        )
        result = self.evaluate(spec, [])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["acceptable_scope"], ["Attendance details may be omitted."])

    def test_invalid_evidence_handle(self):
        result = self.evaluate(
            obligation(),
            [{"text": "Sarah Thomas coordinated C-START.", "citation_refs": ["E9"]}],
        )
        self.assertEqual(result["invalid_evidence_handles"], ["E9"])
        self.assertEqual(result["status"], "FAIL")

    def test_deterministic_and_immutable(self):
        spec = obligation()
        claims = [{"text": "Sarah Thomas coordinated C-START.", "citation_refs": ["E1"]}]
        original = deepcopy(claims)
        first = self.evaluate(spec, claims)
        second = self.evaluate(spec, claims)
        self.assertEqual(first, second)
        self.assertEqual(claims, original)


if __name__ == "__main__":
    unittest.main()
