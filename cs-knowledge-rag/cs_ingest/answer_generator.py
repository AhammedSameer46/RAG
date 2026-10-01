"""Provider-independent interface for evidence-grounded answer generators."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AnswerGenerator(Protocol):
    """Generate a claim answer from compact model-facing context."""

    def generate(
        self, question: str, evidence_response: dict[str, Any]
    ) -> dict[str, Any]:
        """Return the internal claim answer contract."""
        ...
