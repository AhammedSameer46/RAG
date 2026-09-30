import unittest
from copy import deepcopy

from evaluation.step10b_runner import _build_artifact, _run_one


class FakePipeline:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def run(self, question):
        del question
        if self.error:
            raise self.error
        return self.result


class FakeCapture:
    internal_output = {
        "status": "answered",
        "claims": [{"text": "Sarah Thomas coordinated C-START.", "citation_refs": ["E1"]}],
    }
    request_payload = None
    raw_response = None
    http_status = 200
    eval_count = 10
    done_reason = "stop"


class Step10BRunnerTests(unittest.TestCase):
    def obligation(self):
        return {
            "id": "E006",
            "question": "Q",
            "required_observations": [],
            "required_evidence_relationships": [],
            "conflict_requirements": [],
            "lifecycle_requirements": [],
            "direct_citation_requirements": [],
        }

    def test_all_results_and_metrics_are_preserved(self):
        result = _run_one(
            FakePipeline({
                "answer": {"status": "answered"},
                "validation": {"valid": True},
                "evidence_response": {
                    "answer_context": {
                        "supporting_evidence": [
                            {"evidence_id": "id", "filename": "x", "page": 1}
                        ],
                        "independent_evidence": [],
                    },
                    "selection": {
                        "selected_evidence_ids": ["id"],
                        "coverage": {},
                        "truncated": False,
                    },
                },
            }),
            FakeCapture(),
            {"id": "E006", "question": "Q", "expected_status": "answerable"},
            self.obligation(),
        )
        artifact = _build_artifact([result])
        self.assertEqual(artifact["summary"]["total_questions"], 1)
        self.assertEqual(result["obligation_evaluation"]["status"], "PASS")

    def test_non_answerable_is_not_applicable(self):
        result = _run_one(
            FakePipeline({
                "answer": {"status": "clarification_required"},
                "validation": {"valid": True},
                "evidence_response": {},
            }),
            FakeCapture(),
            {"id": "E008", "question": "Q", "expected_status": "clarification_required"},
            None,
        )
        self.assertEqual(result["obligation_evaluation"]["status"], "N/A")

    def test_model_failure_does_not_crash(self):
        result = _run_one(
            FakePipeline(error=RuntimeError("provider failed")),
            FakeCapture(),
            {"id": "E006", "question": "Q", "expected_status": "answerable"},
            self.obligation(),
        )
        self.assertIsNotNone(result["model_api_failure"])
        self.assertEqual(result["obligation_evaluation"]["status"], "N/A")

    def test_repeated_artifact_build_is_deterministic_and_input_unchanged(self):
        result = _run_one(
            FakePipeline({
                "answer": {"status": "answered"},
                "validation": {"valid": True},
                "evidence_response": {
                    "answer_context": {
                        "supporting_evidence": [],
                        "independent_evidence": [],
                    },
                    "selection": {"coverage": {}, "truncated": False},
                },
            }),
            FakeCapture(),
            {"id": "E006", "question": "Q", "expected_status": "answerable"},
            self.obligation(),
        )
        original = deepcopy(result)
        self.assertEqual(_build_artifact([result]), _build_artifact([result]))
        self.assertEqual(result, original)

    def test_step9_style_configuration_is_fixed(self):
        result = _build_artifact([])
        self.assertEqual(result["run_config"]["attempts_per_question"], 1)
        self.assertEqual(result["run_config"]["retry_policy"], "none")
        self.assertEqual(result["run_config"]["selector"]["max_evidence_units"], 3)
