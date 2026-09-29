from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from pypdf import PdfReader

DATE_PATTERNS = (
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
    re.compile(r"\b\d{1,2}-[A-Za-z]{3}-\d{4}\b"),
    re.compile(
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{4}\b",
        re.IGNORECASE,
    ),
)
MONTH_FORMATS = ("%d/%m/%Y", "%d-%b-%Y", "%d %B %Y")
NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_date(value: str) -> str | None:
    cleaned = value.strip()
    for pattern, fmt in zip(DATE_PATTERNS, MONTH_FORMATS):
        if pattern.fullmatch(cleaned):
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                return None
    return None


def _date_role(context: str) -> str | None:
    lowered = context.lower()
    labels = (
        ("originally scheduled", "original_date"),
        ("notice circulated", "document_issue_date"),
        ("report submitted", "report_submission_date"),
        ("rescheduled", "rescheduled_date"),
        ("meeting date", "meeting_date"),
        ("next meeting", "next_meeting_date"),
        ("start date", "start_date"),
        ("end date", "end_date"),
        ("due date", "action_due_date"),
        ("event date", "event_date"),
    )
    for label, role in labels:
        if label in lowered:
            return role
    if "event" in lowered or "programme" in lowered or "program" in lowered:
        return "event_date"
    return None


def _date_candidates(
    text: str, source: str, provenance: dict[str, Any], context: str = ""
) -> list[dict[str, Any]]:
    candidates = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            original = match.group(0)
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            local_context = text[line_start:line_end]
            role_context = local_context if "\n" in text else (context or local_context)
            candidate = {
                "original_text": original,
                "normalized_iso": normalize_date(original),
                "date_role": _date_role(role_context),
                "source": source,
                "provenance": provenance,
            }
            candidates.append(candidate)
    return candidates


def _pdf_text(path: Path) -> list[dict[str, Any]]:
    pages = []
    reader = PdfReader(str(path))
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(
            {
                "source": path.name,
                "page_number": page_number,
                "text": text,
                "provenance": {"source": path.name, "page": page_number},
            }
        )
    return pages


def _column_number(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter) - ord("A") + 1
    return result


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.findall(".//main:t", NS))
        for item in root.findall("main:si", NS)
    ]


def _workbook_sheets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall("rel:Relationship", REL_NS)
    }
    sheets = []
    for sheet in workbook.findall("main:sheets/main:sheet", NS):
        target = targets[
            sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        ].lstrip("/")
        sheets.append((sheet.attrib["name"], target if target.startswith("xl/") else "xl/" + target))
    return sheets


def _xlsx_sheets(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    worksheets = []
    dates = []
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        for sheet_name, sheet_path in _workbook_sheets(archive):
            root = ElementTree.fromstring(archive.read(sheet_path))
            rows = []
            headers: dict[int, str] = {}
            for row in root.findall("main:sheetData/main:row", NS):
                cells = []
                values: dict[str, str] = {}
                for cell in row.findall("main:c", NS):
                    reference = cell.attrib["r"]
                    value_node = cell.find("main:v", NS)
                    inline = cell.find("main:is/main:t", NS)
                    value = inline.text if inline is not None else (value_node.text if value_node is not None else "")
                    if cell.attrib.get("t") == "s" and value:
                        value = strings[int(value)]
                    column = re.match(r"[A-Z]+", reference).group(0)
                    values[column] = value or ""
                    cells.append({"cell": reference, "value": value or ""})
                if row.attrib["r"] == "1":
                    headers = {column: value for column, value in values.items()}
                row_record = {
                    "row_number": int(row.attrib["r"]),
                    "cells": cells,
                    "values": values,
                    "header_context": headers.copy(),
                    "provenance": {
                        "source": path.name,
                        "sheet": sheet_name,
                        "row": int(row.attrib["r"]),
                        "cell_range": (
                            f"{min(values, key=_column_number)}:{max(values, key=_column_number)}"
                            if values
                            else ""
                        ),
                    },
                }
                rows.append(row_record)
                if row.attrib["r"] != "1":
                    for column, value in values.items():
                        header = headers.get(column, "")
                        context = f"{header}: {value}"
                        dates.extend(
                            _date_candidates(
                                value,
                                path.name,
                                {
                                    **row_record["provenance"],
                                    "cell": f"{column}{row.attrib['r']}",
                                },
                                context,
                            )
                        )
            worksheets.append(
                {
                    "source": path.name,
                    "sheet_name": sheet_name,
                    "rows": rows,
                    "provenance": {"source": path.name, "sheet": sheet_name},
                }
            )
    return worksheets, dates


def ingest_directory(input_dir: str | Path, output_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(input_dir)
    files = sorted(path for path in root.iterdir() if path.suffix.lower() in {".pdf", ".xlsx"})
    result: dict[str, Any] = {
        "schema_version": 1,
        "sources": [],
        "pdf_pages": [],
        "worksheets": [],
        "dates": [],
    }
    for path in files:
        source = {
            "filename": path.name,
            "file_type": path.suffix.lower().lstrip("."),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        result["sources"].append(source)
        if path.suffix.lower() == ".pdf":
            pages = _pdf_text(path)
            result["pdf_pages"].extend(pages)
            for page in pages:
                result["dates"].extend(
                    _date_candidates(
                        page["text"], path.name, page["provenance"], page["text"]
                    )
                )
        else:
            worksheets, dates = _xlsx_sheets(path)
            result["worksheets"].extend(worksheets)
            result["dates"].extend(dates)
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract local PDF and XLSX sample data.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    result = ingest_directory(args.input_dir, args.output)
    print(f"Processed {len(result['sources'])} files; wrote {args.output}")


if __name__ == "__main__":
    main()
