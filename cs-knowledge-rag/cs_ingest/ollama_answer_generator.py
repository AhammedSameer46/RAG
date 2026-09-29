"""Small HTTP adapter for a local Ollama answer generator."""

from __future__ import annotations

import json
import socket
from typing import Any
from urllib import error, request

from .answer_generator import AnswerGenerator

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
            return {"status": status, "answer": "", "citations": []}
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
    return (
        "Question:\n"
        + question
        + "\n\nEvidence response (JSON):\n"
        + json.dumps(evidence_response, sort_keys=True)
    )


def _parse_response(response_body: bytes) -> dict[str, Any]:
    try:
        envelope = json.loads(response_body.decode("utf-8"))
        model_text = envelope["response"]
        answer = json.loads(model_text)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OllamaResponseError("Ollama returned malformed JSON.") from exc
    if not isinstance(answer, dict):
        raise OllamaResponseError("Ollama answer must be a JSON object.")
    required = {"status", "answer", "citations"}
    if not required.issubset(answer):
        raise OllamaResponseError("Ollama answer is missing required fields.")
    if answer["status"] not in _STATUSES:
        raise OllamaResponseError("Ollama answer status is unsupported.")
    return answer


_SYSTEM_PROMPT = """You answer questions about institutional records.
Use ONLY the supplied evidence response. Do not use outside knowledge, invent
facts, or infer unsupported facts. If evidence is insufficient, do not
fabricate an answer. Preserve conflicting source observations. Every factual
claim must be supported by supplied evidence. Use only supplied
evidence_id, source_id, and location values; never invent citation identifiers.
Return ONLY the required JSON answer object with status, answer, and citations.
"""


assert isinstance(OllamaAnswerGenerator(), AnswerGenerator)
