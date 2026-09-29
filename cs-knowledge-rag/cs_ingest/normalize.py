"""Normalize extraction output into source-linked local records."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .ingest import normalize_date


def _source_id(source: dict[str, Any]) -> str:
    return f"sha256:{source['sha256']}"


def _source_lookup(data: dict[str, Any]) -> dict[str, str]:
    return {source["filename"]: _source_id(source) for source in data["sources"]}


def _pdf_evidence_id(source_id: str, page: int) -> str:
    return f"{source_id}:pdf-page:{page}"


def _row_evidence_id(source_id: str, sheet: str, row: int) -> str:
    return f"{source_id}:sheet:{sheet}:row:{row}"


def _cell_evidence_id(source_id: str, sheet: str, cell: str) -> str:
    return f"{source_id}:sheet:{sheet}:cell:{cell}"


def _evidence_ref(evidence_id: str) -> dict[str, str]:
    return {"evidence_id": evidence_id}


def _record_id(record_type: str, *parts: str) -> str:
    normalized = "-".join(re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-") for part in parts)
    return f"{record_type}:{normalized}"


def _pdf_evidence(data: dict[str, Any], source_ids: dict[str, str]) -> list[dict[str, Any]]:
    evidence = []
    for page in data["pdf_pages"]:
        source_id = source_ids[page["source"]]
        evidence.append(
            {
                "source_id": source_id,
                "evidence_id": _pdf_evidence_id(source_id, page["page_number"]),
                "kind": "pdf_page",
                "page": page["page_number"],
                "extracted_text": page["text"],
            }
        )
    return evidence


def _worksheet_evidence(
    data: dict[str, Any], source_ids: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], str]]:
    evidence = []
    row_ids: dict[tuple[str, str, int], str] = {}
    for worksheet in data["worksheets"]:
        source_id = source_ids[worksheet["source"]]
        sheet = worksheet["sheet_name"]
        for row in worksheet["rows"]:
            row_number = row["row_number"]
            row_id = _row_evidence_id(source_id, sheet, row_number)
            row_ids[(worksheet["source"], sheet, row_number)] = row_id
            evidence.append(
                {
                    "source_id": source_id,
                    "evidence_id": row_id,
                    "kind": "worksheet_row",
                    "sheet": sheet,
                    "row": row_number,
                    "cell_range": row["provenance"]["cell_range"],
                    "raw_values": row["values"],
                    "header_context": row["header_context"],
                }
            )
            if sheet == "Faculty Attendance" and row_number > 1:
                for cell in row["cells"][1:]:
                    cell_id = _cell_evidence_id(source_id, sheet, cell["cell"])
                    evidence.append(
                        {
                            "source_id": source_id,
                            "evidence_id": cell_id,
                            "kind": "worksheet_cell",
                            "sheet": sheet,
                            "row": row_number,
                            "cell": cell["cell"],
                            "raw_values": {
                                "faculty": row["values"].get("A"),
                                "meeting_header": row["header_context"].get(
                                    cell["cell"].rstrip("0123456789")
                                ),
                                "attendance_value": cell["value"],
                            },
                            "header_context": row["header_context"],
                        }
                    )
    return evidence, row_ids


def _date_mentions(data: dict[str, Any], source_ids: dict[str, str]) -> list[dict[str, Any]]:
    mentions = []
    for item in data["dates"]:
        provenance = item["provenance"]
        source_id = source_ids[item["source"]]
        if "page" in provenance:
            evidence_id = _pdf_evidence_id(source_id, provenance["page"])
        elif "cell" in provenance:
            evidence_id = _row_evidence_id(
                source_id, provenance["sheet"], provenance["row"]
            )
        else:
            continue
        mentions.append(
            {
                "original_text": item["original_text"],
                "normalized_iso": item["normalized_iso"],
                "date_role": item["date_role"],
                "evidence_id": evidence_id,
            }
        )
    return mentions


def _meeting_records(
    data: dict[str, Any], source_ids: dict[str, str], row_ids: dict[tuple[str, str, int], str]
) -> list[dict[str, Any]]:
    records = []
    for worksheet in data["worksheets"]:
        if worksheet["sheet_name"] != "Meeting Log":
            continue
        for row in worksheet["rows"][1:]:
            values = row["values"]
            meeting_date = normalize_date(values["A"])
            record = {
                "record_id": _record_id("meeting", meeting_date or values["A"], values["B"]),
                "record_type": "meeting",
                "attributes": {
                    "meeting_date": meeting_date,
                    "meeting_type": values["B"],
                    "chair": values["C"],
                    "attendees_count": int(values["D"]),
                    "key_decision": values["E"],
                },
                "evidence_refs": [
                    _evidence_ref(row_ids[(worksheet["source"], worksheet["sheet_name"], row["row_number"])])
                ],
            }
            for page in data["pdf_pages"]:
                if meeting_date and meeting_date in {
                    mention["normalized_iso"]
                    for mention in data["dates"]
                    if mention["source"] == page["source"]
                    and mention["date_role"] == "meeting_date"
                    and "page" in mention["provenance"]
                } and "Minutes of Department Meeting" in page["text"]:
                    record["evidence_refs"].append(
                        _evidence_ref(_pdf_evidence_id(source_ids[page["source"]], page["page_number"]))
                    )
            records.append(record)
    return records


def _event_records(
    data: dict[str, Any], source_ids: dict[str, str], row_ids: dict[tuple[str, str, int], str]
) -> list[dict[str, Any]]:
    records = []
    for worksheet in data["worksheets"]:
        if worksheet["sheet_name"] != "Events":
            continue
        for row in worksheet["rows"][1:]:
            values = row["values"]
            start_date = normalize_date(values["B"])
            end_date = normalize_date(values["C"])
            attributes: dict[str, Any] = {
                "name": values["A"],
                "start_date": start_date,
                "end_date": end_date,
                "coordinator": values["D"],
                "participants": int(values["E"]),
                "status": values["F"],
            }
            evidence_refs = [
                _evidence_ref(row_ids[(worksheet["source"], worksheet["sheet_name"], row["row_number"])])
            ]
            for page in data["pdf_pages"]:
                if "C-START" in page["text"] and "C-START" in values["A"]:
                    pdf_id = _pdf_evidence_id(source_ids[page["source"]], page["page_number"])
                    evidence_refs.append(_evidence_ref(pdf_id))
                    matches = re.findall(
                        r"(45 third-year students attended|45 students from the third and fourth year batches participated)",
                        page["text"],
                    )
                    if matches:
                        observations = attributes.setdefault("participant_observations", [])
                        observations.extend(
                            {
                                "source_statement": statement,
                                "participants": 45,
                                "evidence_id": pdf_id,
                            }
                            for statement in matches
                        )
            records.append(
                {
                    "record_id": _record_id("event", start_date or values["B"], values["A"]),
                    "record_type": "event",
                    "attributes": attributes,
                    "evidence_refs": evidence_refs,
                }
            )
    return records


def _attendance_records(
    data: dict[str, Any], source_ids: dict[str, str]
) -> list[dict[str, Any]]:
    records = []
    for worksheet in data["worksheets"]:
        if worksheet["sheet_name"] != "Faculty Attendance":
            continue
        source_id = source_ids[worksheet["source"]]
        header = worksheet["rows"][0]["values"]
        for row in worksheet["rows"][1:]:
            person = row["values"]["A"]
            for column, value in row["values"].items():
                if column == "A":
                    continue
                meeting_header = header[column]
                date_text = meeting_header.split(" ", 1)[0]
                meeting_date = normalize_date(date_text)
                cell = f"{column}{row['row_number']}"
                evidence_id = _cell_evidence_id(source_id, worksheet["sheet_name"], cell)
                records.append(
                    {
                        "record_id": _record_id("attendance", meeting_date or date_text, person),
                        "record_type": "attendance",
                        "attributes": {
                            "person": person,
                            "meeting_date": meeting_date,
                            "meeting_label": meeting_header,
                            "status": value,
                            "remarks": None,
                        },
                        "evidence_refs": [_evidence_ref(evidence_id)],
                    }
                )
    return records


def normalize_ingestion(data: dict[str, Any]) -> dict[str, Any]:
    """Convert the existing extraction JSON into the normalized local model."""
    source_ids = _source_lookup(data)
    evidence = _pdf_evidence(data, source_ids)
    worksheet_evidence, row_ids = _worksheet_evidence(data, source_ids)
    evidence.extend(worksheet_evidence)
    return {
        "schema_version": 1,
        "sources": [
            {
                "source_id": source_ids[source["filename"]],
                "filename": source["filename"],
                "file_type": source["file_type"],
                "sha256": source["sha256"],
                "size_bytes": source["size_bytes"],
            }
            for source in data["sources"]
        ],
        "evidence_units": evidence,
        "date_mentions": _date_mentions(data, source_ids),
        "records": (
            _meeting_records(data, source_ids, row_ids)
            + _event_records(data, source_ids, row_ids)
            + _attendance_records(data, source_ids)
        ),
    }


def normalize_json_file(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    normalized = normalize_ingestion(data)
    Path(output_path).write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize extraction JSON.")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    normalized = normalize_json_file(args.input, args.output)
    print(f"Normalized {len(normalized['sources'])} sources into {args.output}")


if __name__ == "__main__":
    main()
