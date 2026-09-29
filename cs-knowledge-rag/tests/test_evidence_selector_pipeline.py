import unittest
from copy import deepcopy
from pathlib import Path

from cs_ingest.answer_pipeline import AnswerPipeline
from cs_ingest.evidence_response import build_evidence_response
from cs_ingest.evidence_selector import EvidenceSelectionConfig, EvidenceSelector
from cs_ingest.pipeline import QueryRetrievalPipeline


ROOT = Path(__file__).parents[1]


def _citation(evidence):
    return {
        "evidence_id": evidence["evidence_id"],
        "source_id": evidence["source_id"],
        "filename": evidence["filename"],
        "location": {
            field: evidence[field]
            for field in ("page", "sheet", "row", "cell", "cell_range")
            if field in evidence
        },
    }


class RecordingGenerator:
    def __init__(self, citation_source="selected"):
        self.evidence_response = None
        self.citation_source = citation_source

    def generate(self, question, evidence_response):
        del question
        self.evidence_response = evidence_response
        evidence = evidence_response["answer_context"]["supporting_evidence"][0]
        if self.citation_source == "excluded":
            evidence = self.excluded_evidence
        return {
            "status": "answered",
            "answer": "Grounded answer.",
            "citations": [_citation(evidence)],
        }


class CountingGenerator:
    def __init__(self):
        self.called = False

    def generate(self, question, evidence_response):
        del question, evidence_response
        self.called = True
        return {"status": "answered", "answer": "unexpected", "citations": []}


class EvidenceSelectorPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query_pipeline = QueryRetrievalPipeline.from_json(
            ROOT / "output" / "sample_normalized.json"
        )
        cls.config = EvidenceSelectionConfig(
            max_evidence_units=3,
            max_characters=12000,
            max_records=8,
        )

    def make_pipeline(self, generator, selector=True):
        return AnswerPipeline(
            self.query_pipeline,
            generator,
            EvidenceSelector() if selector else None,
            self.config if selector else None,
        )

    def test_selector_disabled_preserves_existing_behavior(self):
        generator = RecordingGenerator()
        result = self.make_pipeline(generator, selector=False).run(
            "What happened on 18 July 2026?"
        )
        self.assertTrue(result["validation"]["valid"])
        self.assertNotIn("selection", result["evidence_response"])

    def test_selector_enabled_sends_only_selected_context(self):
        generator = RecordingGenerator()
        result = self.make_pipeline(generator).run(
            "What happened on 18 July 2026?"
        )
        supplied_ids = {
            evidence["evidence_id"]
            for collection in (
                generator.evidence_response["answer_context"][
                    "supporting_evidence"
                ],
                generator.evidence_response["answer_context"][
                    "independent_evidence"
                ],
            )
            for evidence in collection
        }
        selected_ids = set(
            generator.evidence_response["selection"]["selected_evidence_ids"]
        )
        self.assertEqual(supplied_ids, selected_ids)
        self.assertEqual(
            generator.evidence_response["selection"]["selected_count"], 3
        )
        self.assertTrue(result["validation"]["valid"])

    def test_excluded_evidence_cannot_be_cited(self):
        generator = RecordingGenerator("excluded")
        unrestricted = self.make_pipeline(RecordingGenerator()).run(
            "What happened on 18 July 2026?"
        )
        excluded_ids = set(
            unrestricted["evidence_response"]
            .get("selection", {})
            .get("excluded_evidence_ids", [])
        )
        self.assertTrue(excluded_ids)
        full_response = build_evidence_response(
            self.query_pipeline.run("What happened on 18 July 2026?")
        )
        generator.excluded_evidence = next(
            evidence
            for evidence in (
                full_response["answer_context"]["supporting_evidence"]
                + full_response["answer_context"]["independent_evidence"]
            )
            if evidence["evidence_id"] in excluded_ids
        )
        result = self.make_pipeline(generator).run(
            "What happened on 18 July 2026?"
        )
        self.assertFalse(result["validation"]["valid"])
        self.assertIn(
            "UNKNOWN_EVIDENCE_ID",
            {error["code"] for error in result["validation"]["errors"]},
        )

    def test_selected_provenance_and_metadata_are_preserved(self):
        generator = RecordingGenerator()
        result = self.make_pipeline(generator).run(
            "What happened on 18 July 2026?"
        )
        response = generator.evidence_response
        self.assertEqual(
            response["selection"]["selected_evidence_ids"],
            result["evidence_response"]["selection"]["selected_evidence_ids"],
        )
        for collection in (
            response["answer_context"]["supporting_evidence"],
            response["answer_context"]["independent_evidence"],
        ):
            for evidence in collection:
                self.assertTrue(evidence["evidence_id"])
                self.assertTrue(evidence["source_id"])
                self.assertTrue(
                    any(
                        field in evidence
                        for field in ("page", "sheet", "row", "cell", "cell_range")
                    )
                )
        self.assertIn("coverage", response["selection"])
        self.assertIn("truncated", response["selection"])
        self.assertIn("conflict_flags", response["selection"])

    def test_clarification_does_not_call_selector_generator(self):
        generator = CountingGenerator()
        result = self.make_pipeline(generator).run("What happened on 18 July?")
        self.assertFalse(generator.called)
        self.assertEqual(result["answer"]["status"], "clarification_required")
        self.assertTrue(result["validation"]["valid"])

    def test_insufficient_evidence_does_not_call_selector_generator(self):
        generator = CountingGenerator()
        result = self.make_pipeline(generator).run("What happened on 10 January 2099?")
        self.assertFalse(generator.called)
        self.assertEqual(result["answer"]["status"], "insufficient_evidence")
        self.assertTrue(result["validation"]["valid"])

    def test_cstart_conflict_can_survive_selection(self):
        generator = RecordingGenerator()
        pipeline = AnswerPipeline(
            self.query_pipeline,
            generator,
            EvidenceSelector(),
            EvidenceSelectionConfig(
                max_evidence_units=20,
                max_characters=100000,
                max_records=8,
            ),
        )
        result = pipeline.run("What happened on 18 July 2026?")
        flags = result["evidence_response"]["selection"]["conflict_flags"]
        self.assertTrue(
            any(flag["dimension"] == "participant_category" for flag in flags)
        )
        conflict_ids = {
            evidence_id
            for flag in flags
            for evidence_id in flag["evidence_ids"]
        }
        self.assertTrue(
            conflict_ids.issubset(
                set(result["evidence_response"]["selection"]["selected_evidence_ids"])
            )
        )

    def test_original_evidence_response_is_not_mutated_by_selection(self):
        generator = RecordingGenerator()
        pipeline = self.make_pipeline(generator)
        result = pipeline.run("What happened on 18 July 2026?")
        selected_response = result["evidence_response"]
        snapshot = deepcopy(selected_response["answer_context"])
        selected_response["answer_context"]["records"].clear()
        self.assertNotEqual(selected_response["answer_context"], snapshot)
        rerun = self.make_pipeline(RecordingGenerator()).run(
            "What happened on 18 July 2026?"
        )
        self.assertEqual(
            rerun["evidence_response"]["selection"]["selected_count"], 3
        )


if __name__ == "__main__":
    unittest.main()
