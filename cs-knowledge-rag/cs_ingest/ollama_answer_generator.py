"""Small HTTP adapter for a local Ollama answer generator."""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib import error, request

from .answer_generator import AnswerGenerator
from .citation_builder import citation_handles

_STATUSES = {"answered", "insufficient_evidence", "clarification_required"}
_DEFAULT_MODEL = "SET_OLLAMA_MODEL"


class OllamaProviderError(RuntimeError):
    """Base error for deterministic Ollama provider failures."""


class OllamaConnectionError(OllamaProviderError):
    """The Ollama endpoint could not be reached."""


class OllamaTimeoutError(OllamaProviderError):
    """The Ollama request exceeded its configured timeout."""


class OllamaHTTPError(OllamaProviderError):
    """Ollama returned an HTTP error."""


class OllamaResponseError(OllamaProviderError):
    """Ollama returned an invalid answer payload."""


class OllamaAnswerGenerator:
    """Generate answer-contract objects through Ollama's local HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = _DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(
        self, question: str, evidence_response: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an answer, or raise an explicit provider error."""
        status = evidence_response.get("status")
        if status in {"clarification_required", "insufficient_evidence"}:
            return {"status": status, "answer": "", "citation_refs": []}
        if status != "answerable":
            raise OllamaResponseError("Evidence response status is unsupported.")

        payload = {
            "model": self.model,
            "system": _SYSTEM_PROMPT,
            "prompt": _user_prompt(question, evidence_response),
            "format": "json",
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                response_body = response.read()
        except socket.timeout as exc:
            raise OllamaTimeoutError("Ollama request timed out.") from exc
        except TimeoutError as exc:
            raise OllamaTimeoutError("Ollama request timed out.") from exc
        except error.HTTPError as exc:
            raise OllamaHTTPError(f"Ollama returned HTTP status {exc.code}.") from exc
        except error.URLError as exc:
            raise OllamaConnectionError("Ollama endpoint could not be reached.") from exc
        return _parse_response(response_body)


def _user_prompt(question: str, evidence_response: dict[str, Any]) -> str:
    context = _model_answer_context(evidence_response)
    return (
        "Question:\n"
        + question
        + "\n\nEvidence context (JSON):\n"
        + json.dumps(context, sort_keys=True)
    )


def _model_answer_context(evidence_response: dict[str, Any]) -> dict[str, Any]:
    context = json.loads(json.dumps(evidence_response["answer_context"]))
    handles = citation_handles(evidence_response)
    for collection in ("supporting_evidence", "independent_evidence"):
        wrapped = []
        for evidence in context.get(collection, []):
            handle = next(
                handle
                for handle, selected in handles.items()
                if selected["evidence_id"] == evidence["evidence_id"]
            )
            wrapped.append({"citation_ref": handle, "evidence": evidence})
        context[collection] = wrapped
    return context


def _parse_response(response_body: bytes) -> dict[str, Any]:
    try:
        envelope = json.loads(response_body.decode("utf-8"))
        model_text = envelope["response"]
        answer = json.loads(model_text)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OllamaResponseError("Ollama returned malformed JSON.") from exc
    if not isinstance(answer, dict):
        raise OllamaResponseError("Ollama answer must be a JSON object.")
    required = {"status", "answer", "citation_refs"}
    if set(answer) != required:
        raise OllamaResponseError("Ollama answer is missing required fields.")
    if answer["status"] not in _STATUSES:
        raise OllamaResponseError("Ollama answer status is unsupported.")
    if not isinstance(answer["citation_refs"], list):
        raise OllamaResponseError("Ollama citation_refs must be a list.")
    return answer


_SYSTEM_PROMPT = """You answer questions about institutional records.

Use ONLY the supplied evidence response.
Do not use outside knowledge.
Do not invent facts.
Do not infer unsupported facts.
Preserve conflicting source observations.
Every factual claim must be supported by the supplied evidence.

Return ONLY one JSON object with EXACTLY these three top-level fields:

{
  "status": "answered | insufficient_evidence | clarification_required",
  "answer": "string",
  "citation_refs": ["E1", "E2"]
}

Rules:

- For an answerable question, status MUST be exactly "answered".
- For insufficient evidence, status MUST be exactly "insufficient_evidence".
- For a clarification request, status MUST be exactly "clarification_required".
- answer MUST be a non-empty string for status "answered".
- For status "insufficient_evidence" or "clarification_required", answer MUST be an empty string.
- citation_refs MUST be a non-empty array when status is "answered".
- citation_refs MUST be an empty array for status "insufficient_evidence" or "clarification_required".
- Every citation ref MUST exactly match a citation_ref handle supplied in the evidence context.
- Never output source IDs, evidence IDs, filenames, or locations.
- Do not fabricate citation refs.
- Do not add extra top-level fields.
- Do not output markdown.
- Do not output prose outside the JSON object.
- Do not add confidence.
- Do not add query_understanding.
- Do not add sources.
- Do not add selection metadata.

The application will deterministically attach exact provenance after generation.
"""


assert isinstance(OllamaAnswerGenerator(), AnswerGenerator)
