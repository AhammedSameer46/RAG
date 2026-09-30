import copy
import unittest
from pathlib import Path

from cs_ingest.claim_answer_contract import (
    ClaimAnswerContractError,
    validate_claim_answer,
)
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


class ClaimAnswerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.response = build_evidence_response(
            pipeline.run("What happened on 18 July 2026?")
        )

    def claim(self, refs=("E1",), text="Dr. Reena Nair was present."):
        return {"text": text, "citation_refs": list(refs)}

    def test_valid_answered_claims(self):
        self.assertEqual(
            validate_claim_answer(
                {"status": "answered", "claims": [self.claim()]},
                self.response,
            ),
            {"valid": True, "errors": []},
        )

    def test_multiple_claims_and_empty_answered_claims(self):
        valid = {"status": "answered", "claims": [self.claim(), self.claim(("E2",))]}
        self.assertTrue(validate_claim_answer(valid, self.response)["valid"])
        with self.assertRaises(ClaimAnswerContractError):
            validate_claim_answer({"status": "answered", "claims": []}, self.response)

    def test_missing_or_unknown_refs(self):
        for claim in (
            {"text": "Fact.", "citation_refs": []},
            {"text": "Fact.", "citation_refs": ["E99"]},
        ):
            with self.assertRaises(ClaimAnswerContractError):
                validate_claim_answer(
                    {"status": "answered", "claims": [claim]}, self.response
                )

    def test_invalid_status_and_non_answerable_claims(self):
        with self.assertRaises(ClaimAnswerContractError):
            validate_claim_answer({"status": "unknown", "claims": []}, self.response)
        for status in ("clarification_required", "insufficient_evidence"):
            with self.assertRaises(ClaimAnswerContractError):
                validate_claim_answer(
                    {"status": status, "claims": [self.claim()]}, self.response
                )

    def test_raw_provenance_and_malformed_claims_are_rejected(self):
        bad_claims = [
            {"text": "Fact.", "citation_refs": ["E1"], "page": 1},
            {"text": "", "citation_refs": ["E1"]},
            {"text": "Fact.", "citation_refs": ["E1", "E1"]},
            {"text": "Fact.", "citation_refs": [1]},
        ]
        for claim in bad_claims:
            with self.assertRaises(ClaimAnswerContractError):
                validate_claim_answer(
                    {"status": "answered", "claims": [claim]}, self.response
                )

    def test_input_is_immutable(self):
        output = {"status": "answered", "claims": [self.claim()]}
        snapshot = copy.deepcopy(output)
        validate_claim_answer(output, self.response)
        self.assertEqual(output, snapshot)
