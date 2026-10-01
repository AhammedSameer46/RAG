import copy
import unittest

from cs_ingest.answer_contract import validate_answer
from cs_ingest.answer_plan import build_answer_plan
from cs_ingest.citation_builder import CitationBuilder, citation_handles
from cs_ingest.claim_answer_contract import validate_claim_answer
from cs_ingest.model_facing_context import build_model_facing_context


def _evidence(evidence_id, filename, text, **location):
    return {
        "evidence_id": evidence_id,
        "source_id": f"source-{evidence_id}",
        "filename": filename,
        "extracted_text": text,
        **location,
    }


def _selected_response():
    first = _evidence(
        "pdf-evidence",
        "meeting.pdf",
        "The meeting minutes report 45 third-year students.",
        page=1,
    )
    second = _evidence(
        "sheet-evidence",
        "attendance.xlsx",
        "The attendance sheet records 45 attendees.",
        sheet="Faculty Attendance",
        row=2,
        cell="B2",
    )
    return {
        "status": "answerable",
        "answer_context": {
            "records": [
                {
                    "record_id": "record-1",
                    "record_type": "meeting",
                    "evidence_refs": [{"evidence_id": first["evidence_id"]}],
                },
                {
                    "record_id": "record-2",
                    "record_type": "attendance",
                    "evidence_refs": [{"evidence_id": second["evidence_id"]}],
                },
            ],
            "supporting_evidence": [first],
            "independent_evidence": [second],
        },
        "selection": {
            "coverage": {
                "coverage_complete": True,
                "conflict_groups": [
                    {
                        "coverage_group_id": "conflict:participants",
                        "evidence_ids": [first["evidence_id"], second["evidence_id"]],
                        "complete": True,
                    }
                ],
                "lifecycle_groups": [],
                "excluded_evidence_ids": [],
            }
        },
    }


class ModelFacingContextIntegrationTests(unittest.TestCase):
    def test_offline_conflict_flow_restores_exact_public_citations(self):
        response = _selected_response()
        response["answer_plan"] = build_answer_plan(response)
        context = build_model_facing_context(response)

        self.assertEqual(
            context["answer_plan"]["observations"],
            [
                {"evidence_ids": ["E1"], "preserve_separately": True},
                {"evidence_ids": ["E2"], "preserve_separately": True},
            ],
        )
        self.assertEqual(
            context["answer_plan"]["conflict_groups"],
            [{"observation_indexes": [0, 1], "must_preserve_separately": True}],
        )
        self.assertEqual(
            [item["id"] for item in context["evidence"]],
            list(citation_handles(response)),
        )

        claims = {
            "status": "answered",
            "claims": [
                {"text": "The minutes report 45 third-year students.", "citation_refs": ["E1"]},
                {"text": "The attendance sheet records 45 attendees.", "citation_refs": ["E2"]},
            ],
        }
        self.assertEqual(validate_claim_answer(claims, response), {"valid": True, "errors": []})
        answer = CitationBuilder().build(claims, response)
        self.assertEqual(answer["citations"][0]["evidence_id"], "pdf-evidence")
        self.assertEqual(answer["citations"][0]["location"], {"page": 1})
        self.assertEqual(answer["citations"][1]["evidence_id"], "sheet-evidence")
        self.assertEqual(
            answer["citations"][1]["location"],
            {"sheet": "Faculty Attendance", "row": 2, "cell": "B2"},
        )
        self.assertEqual(validate_answer(answer, response), {"valid": True, "errors": []})

    def test_builder_does_not_mutate_answer_plan_or_evidence(self):
        response = _selected_response()
        response["answer_plan"] = build_answer_plan(response)
        before = copy.deepcopy(response)
        build_model_facing_context(response)
        self.assertEqual(response, before)

    def test_non_answerable_flow_has_no_factual_context(self):
        response = {
            "status": "clarification_required",
            "answer_context": {
                "records": [],
                "supporting_evidence": [],
                "independent_evidence": [],
            },
        }
        response["answer_plan"] = build_answer_plan(response)
        self.assertEqual(
            build_model_facing_context(response)["evidence"],
            [],
        )
        answer = CitationBuilder().build(
            {"status": "clarification_required", "claims": []},
            response,
        )
        self.assertEqual(answer, {
            "status": "clarification_required",
            "answer": "",
            "citations": [],
        })
        self.assertEqual(validate_answer(answer, response), {"valid": True, "errors": []})
