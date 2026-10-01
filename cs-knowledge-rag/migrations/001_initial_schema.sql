-- Computer Science Knowledge RAG
-- Migration 001: normalized relational persistence foundation.
--
-- Apply this migration once through the project's migration runner.
-- Do not place sample data in migrations.

CREATE TABLE source (
    source_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL UNIQUE,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    CONSTRAINT source_sha256_format_chk
        CHECK (sha256 ~ '^[0-9a-fA-F]{64}$')
);

CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL
        REFERENCES source (source_id),
    kind TEXT NOT NULL
        CHECK (kind IN ('pdf_page', 'worksheet_row', 'worksheet_cell')),
    page INTEGER
        CHECK (page IS NULL OR page > 0),
    sheet TEXT,
    row_number INTEGER
        CHECK (row_number IS NULL OR row_number > 0),
    cell TEXT,
    cell_range TEXT,
    extracted_text TEXT,
    raw_values JSONB,
    header_context JSONB
);

CREATE TABLE record (
    record_id TEXT PRIMARY KEY,
    record_type TEXT NOT NULL
        CHECK (record_type IN ('meeting', 'event', 'attendance')),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(attributes) = 'object')
);

CREATE TABLE record_evidence (
    record_id TEXT NOT NULL
        REFERENCES record (record_id),
    evidence_id TEXT NOT NULL
        REFERENCES evidence (evidence_id),
    PRIMARY KEY (record_id, evidence_id)
);

CREATE TABLE date_mention (
    date_mention_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evidence_id TEXT NOT NULL
        REFERENCES evidence (evidence_id),
    original_text TEXT NOT NULL,
    normalized_iso DATE NOT NULL,
    date_role TEXT
);

CREATE INDEX evidence_source_id_idx
    ON evidence (source_id);

CREATE INDEX evidence_kind_sheet_row_idx
    ON evidence (kind, sheet, row_number);

CREATE INDEX evidence_sheet_cell_idx
    ON evidence (sheet, cell);

CREATE INDEX record_record_type_idx
    ON record (record_type);

CREATE INDEX record_meeting_date_idx
    ON record ((attributes ->> 'meeting_date'));

CREATE INDEX record_event_start_date_idx
    ON record ((attributes ->> 'start_date'));

CREATE INDEX record_event_end_date_idx
    ON record ((attributes ->> 'end_date'));

CREATE INDEX record_attendance_person_idx
    ON record (record_type, (attributes ->> 'person'));

CREATE INDEX record_event_name_idx
    ON record (record_type, (attributes ->> 'name'));

CREATE INDEX date_mention_normalized_iso_idx
    ON date_mention (normalized_iso);

CREATE INDEX date_mention_normalized_iso_role_idx
    ON date_mention (normalized_iso, date_role);

CREATE INDEX date_mention_role_normalized_iso_idx
    ON date_mention (date_role, normalized_iso);

CREATE INDEX date_mention_evidence_id_idx
    ON date_mention (evidence_id);
