"""Provider-independent interface for evidence-grounded answer generators."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AnswerGenerator(Protocol):
    """Generate an existing answer-contract object from an evidence response."""

    def generate(
        self, question: str, evidence_response: dict[str, Any]
    ) -> dict[str, Any]:
        """Return ``status``, ``answer``, and provenance-bearing ``citations``."""
        ...
