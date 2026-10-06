"""Boundary between Google Drive files and the existing ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Protocol

from .ingest import ingest_directory
from .normalize import normalize_ingestion

PDF_MIME_TYPE = "application/pdf"
XLSX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class DriveIngestionError(RuntimeError):
    """Base class for Drive ingestion-boundary errors."""


class UnsupportedDriveFileTypeError(DriveIngestionError):
    """The Drive file is not supported by the existing ingestion pipeline."""


class DriveFileAdapter(Protocol):
    """Minimum adapter contract required by the Drive ingestion boundary."""

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        ...

    def download_file(self, file_id: str) -> bytes:
        ...


@dataclass(frozen=True)
class DriveIngestionInput:
    """Downloaded source bytes plus provenance needed by later ingestion."""

    file_id: str
    filename: str
    file_type: str
    content: bytes
    parent_ids: tuple[str, ...]
    modified_time: str | None
    web_view_link: str | None
    mime_type: str

    @property
    def drive_file_id(self) -> str:
        return self.file_id

    @property
    def drive_file_name(self) -> str:
        return self.filename

    @property
    def drive_mime_type(self) -> str:
        return self.mime_type

    @property
    def drive_parent_ids(self) -> tuple[str, ...]:
        return self.parent_ids

    @property
    def drive_modified_time(self) -> str | None:
        return self.modified_time

    @property
    def drive_web_view_link(self) -> str | None:
        return self.web_view_link

    @property
    def file_bytes(self) -> bytes:
        return self.content


def load_drive_file(
    adapter: DriveFileAdapter,
    file_id: str,
) -> DriveIngestionInput:
    """Load one supported Drive file without parsing or persisting it."""
    metadata = adapter.get_file_metadata(file_id)

    mime_type = metadata.get("mimeType")
    file_type = _file_type_for_mime(mime_type)

    filename = metadata.get("name")
    if not isinstance(filename, str) or not filename:
        raise DriveIngestionError(
            f"Google Drive file {file_id!r} has no usable name."
        )

    parent_ids = metadata.get("parents", [])
    if not isinstance(parent_ids, list) or not all(
        isinstance(parent_id, str) for parent_id in parent_ids
    ):
        raise DriveIngestionError(
            f"Google Drive file {file_id!r} has invalid parent metadata."
        )

    return DriveIngestionInput(
        file_id=file_id,
        filename=filename,
        file_type=file_type,
        content=adapter.download_file(file_id),
        parent_ids=tuple(parent_ids),
        modified_time=_optional_string(metadata.get("modifiedTime")),
        web_view_link=_optional_string(metadata.get("webViewLink")),
        mime_type=mime_type,
    )


def ingest_drive_file(
    adapter: DriveFileAdapter,
    file_id: str,
) -> dict[str, Any]:
    """Materialize one Drive file and process it through local extraction."""
    drive_file = load_drive_file(adapter, file_id)
    result = _extract_drive_file(drive_file)
    _attach_drive_provenance(result, drive_file)
    return result


def normalize_drive_file(
    adapter: DriveFileAdapter,
    file_id: str,
) -> dict[str, Any]:
    """Download, extract, and normalize one supported Drive file."""
    drive_file = load_drive_file(adapter, file_id)
    extracted = _extract_drive_file(drive_file)
    _attach_drive_provenance(extracted, drive_file)
    return normalize_ingestion(extracted)


def _extract_drive_file(
    drive_file: DriveIngestionInput,
) -> dict[str, Any]:
    """Materialize one Drive file temporarily and run local extraction."""
    with tempfile.TemporaryDirectory(prefix="cs-rag-drive-") as temporary_dir:
        file_path = Path(temporary_dir) / drive_file.filename
        file_path.write_bytes(drive_file.content)
        return ingest_directory(temporary_dir)


def _attach_drive_provenance(
    result: dict[str, Any],
    drive_file: DriveIngestionInput,
) -> None:
    """Attach Drive provenance to the matching extracted source."""
    source = next(
        source
        for source in result["sources"]
        if source["filename"] == drive_file.filename
    )

    source["drive_provenance"] = {
        "file_id": drive_file.drive_file_id,
        "file_name": drive_file.drive_file_name,
        "mime_type": drive_file.drive_mime_type,
        "parent_ids": list(drive_file.drive_parent_ids),
        "modified_time": drive_file.drive_modified_time,
        "web_view_link": drive_file.drive_web_view_link,
    }


def _file_type_for_mime(mime_type: Any) -> str:
    if mime_type == PDF_MIME_TYPE:
        return "pdf"

    if mime_type == XLSX_MIME_TYPE:
        return "xlsx"

    raise UnsupportedDriveFileTypeError(
        f"Unsupported Google Drive MIME type: {mime_type!r}. "
        "Only PDF and XLSX files are supported."
    )


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None