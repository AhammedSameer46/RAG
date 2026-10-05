-- Computer Science Knowledge RAG
-- Migration 002: Google Drive synchronization state.
--
-- Apply after migration 001.
-- This migration stores Drive object identity and sync-run state separately
-- from content-oriented normalized sources.

CREATE TABLE drive_sync_run (
    sync_run_id TEXT PRIMARY KEY,
    root_folder_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL
        CHECK (status IN ('running', 'succeeded', 'failed'))
);

CREATE TABLE drive_file (
    drive_file_id TEXT PRIMARY KEY,
    root_folder_id TEXT NOT NULL,
    source_id TEXT
        REFERENCES source (source_id),
    name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    parent_ids JSONB NOT NULL
        CHECK (jsonb_typeof(parent_ids) = 'array'),
    modified_time TIMESTAMPTZ,
    web_view_link TEXT,
    indexed_modified_time TIMESTAMPTZ,
    last_seen_run_id TEXT
        REFERENCES drive_sync_run (sync_run_id),
    last_seen_at TIMESTAMPTZ NOT NULL,
    last_indexed_at TIMESTAMPTZ
);

CREATE INDEX drive_file_root_folder_id_idx
    ON drive_file (root_folder_id);

CREATE INDEX drive_file_last_seen_run_id_idx
    ON drive_file (last_seen_run_id);
