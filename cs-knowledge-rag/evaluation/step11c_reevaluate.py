"""Offline re-evaluation of preserved Step 11B model outputs."""

from __future__ import annotations

import json
from pathlib import Path

from .obligation_evaluator import evaluate_obligations

ROOT = Path(__file__).parents[1]


def reevaluate() -> dict:
    artifact = json.loads(
        (ROOT / "evaluation" / "step11b_smoke_test.json").read_text(
            encoding="utf-8"
        )
    )
    obligations = json.loads(
        (ROOT / "evaluation" / "ANSWER_OBLIGATIONS.json").read_text(
            encoding="utf-8"
        )
    )["obligations"]
    by_id = {item["id"]: item for item in obligations}
    results = []
    for previous in artifact["results"]:
        corrected = evaluate_obligations(
            previous["question"],
            by_id[previous["id"]],
            previous["claim_level_output"],
            previous["citation_handle_mapping"],
            previous["selected_evidence"],
        )
        results.append(
            {
                "id": previous["id"],
                "old_status": previous["obligation_evaluation"]["status"],
                "corrected_status": corrected["status"],
                "old_missing_obligations": previous[
                    "obligation_evaluation"
                ]["missing_obligations"],
                "corrected_missing_obligations": corrected[
                    "missing_obligations"
                ],
                "old_wrong_citation_obligations": previous[
                    "obligation_evaluation"
                ]["wrong_citation_obligations"],
                "corrected_wrong_citation_obligations": corrected[
                    "wrong_citation_obligations"
                ],
                "corrected_evaluation": corrected,
            }
        )
    return {
        "source_artifact": "step11b_smoke_test.json",
        "model_outputs_regenerated": False,
        "results": results,
        "changed_cases": [
            item
            for item in results
            if item["old_status"] != item["corrected_status"]
        ],
    }


def write_report() -> None:
    reevaluation = reevaluate()
    lines = [
        "# STEP 11C Offline Re-evaluation",
        "",
        "This report applies the corrected deterministic phrase normalizer to "
        "the preserved Step 11B model outputs. No model calls were made and "
        "no model output was regenerated.",
        "",
        "## Results",
        "",
        "| ID | Old Step 11B | Corrected | Changed | Reason |",
        "|---|---|---|---|---|",
    ]
    for item in reevaluation["results"]:
        changed = item["old_status"] != item["corrected_status"]
        reason = (
            "number-word normalization changed phrase matching"
            if changed
            else "no classification change"
        )
        lines.append(
            f"| {item['id']} | {item['old_status']} | "
            f"{item['corrected_status']} | {changed} | {reason} |"
        )
    lines.extend(
        [
            "",
            "## Changed cases",
            "",
        ]
    )
    for item in reevaluation["changed_cases"]:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Old missing obligations: `{item['old_missing_obligations']}`",
                f"- Corrected missing obligations: `{item['corrected_missing_obligations']}`",
                f"- Old wrong citations: `{item['old_wrong_citation_obligations']}`",
                f"- Corrected wrong citations: `{item['corrected_wrong_citation_obligations']}`",
                "- Cause: evaluator-only lexical normalization; model behavior and citations were unchanged.",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "- Numeric forms such as `45`, `Forty-five`, and `forty five` are treated as the same explicit number.",
            "- Case, repeated whitespace, and surrounding punctuation are normalized.",
            "- Different numbers, participant categories, lifecycle states, date ranges, evidence sources, and citation correctness remain distinct.",
            "- Step 11B artifacts were not overwritten.",
        ]
    )
    (ROOT / "evaluation" / "STEP11C_REEVALUATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    write_report()
