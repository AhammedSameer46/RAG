from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from cs_ingest.drive_discovery import DriveFileMetadata
from cs_ingest.drive_sync import (
    DriveSyncClassification,
    PreviousDriveFileState,
)
from cs_ingest.drive_sync_orchestration import (
    classify_drive_state,
    discover_drive_inventory,
    persist_successful_drive_state,
    record_drive_sync_failure,
    start_drive_sync_run,
)


ROOT = "root"
STARTED = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
OBSERVED = datetime(2026, 10, 6, 11, tzinfo=timezone.utc)


def _file(file_id: str, modified: str | None = "2026-10-06T10:00:00Z"):
    return DriveFileMetadata(
        file_id, f"{file_id}.pdf", "application/pdf", (ROOT,), modified, None
    )


def _repo(previous=()):
    repository = Mock(
        spec=["save_drive_sync_run", "list_drive_file_states", "save_drive_file"]
    )
    repository.list_drive_file_states.return_value = list(previous)
    return repository


class _TransactionalRepository:
    def __init__(self):
        self.committed_runs = {}
        self.committed_files = {}
        self.pending_runs = {}
        self.pending_files = {}
        self.events = []

    @contextmanager
    def transaction(self):
        self.pending_runs = {}
        self.pending_files = {}
        self.events.append("begin")
        try:
            yield
        except Exception:
            self.pending_runs = {}
            self.pending_files = {}
            self.events.append("rollback")
            raise
        else:
            self.committed_runs.update(self.pending_runs)
            self.committed_files.update(self.pending_files)
            self.events.append("commit")

    def save_drive_sync_run(self, value):
        self.events.append(("run", value["status"]))
        self.pending_runs[value["sync_run_id"]] = dict(value)

    def list_drive_file_states(self, root_folder_id):
        return [
            state
            for state in self.committed_files.values()
            if state.root_folder_id == root_folder_id
        ]

    def save_drive_file(self, value):
        self.events.append(("file", value["drive_file_id"]))
        self.pending_files[value["drive_file_id"]] = dict(value)


def test_explicit_phases_commit_running_before_discovery():
    repository = _TransactionalRepository()
    discovery_events = []

    with repository.transaction():
        start_drive_sync_run(
            repository, sync_run_id="run", root_folder_id=ROOT, started_at=STARTED
        )
    assert repository.committed_runs["run"]["status"] == "running"

    inventory = discover_drive_inventory(
        Mock(),
        ROOT,
        discover=lambda _adapter, _root: (
            discovery_events.append("discover") or [_file("new")]
        ),
    )
    assert discovery_events == ["discover"]
    assert repository.events == ["begin", ("run", "running"), "commit"]

    classifications = classify_drive_state(
        repository, root_folder_id=ROOT, inventory=inventory
    )
    with repository.transaction():
        persist_successful_drive_state(
            repository,
            sync_run_id="run",
            root_folder_id=ROOT,
            started_at=STARTED,
            observed_at=OBSERVED,
            classifications=classifications,
        )
    assert repository.committed_runs["run"]["status"] == "succeeded"


def test_discovery_failure_uses_separate_failure_transaction_and_is_durable():
    repository = _TransactionalRepository()
    with repository.transaction():
        start_drive_sync_run(
            repository, sync_run_id="run", root_folder_id=ROOT, started_at=STARTED
        )

    error = RuntimeError("discovery failed")
    with pytest.raises(RuntimeError, match="discovery failed"):
        discover_drive_inventory(
            Mock(), ROOT, discover=Mock(side_effect=error)
        )

    with repository.transaction():
        record_drive_sync_failure(
            repository,
            sync_run_id="run",
            root_folder_id=ROOT,
            started_at=STARTED,
            completed_at=OBSERVED,
        )
    assert repository.committed_runs["run"]["status"] == "failed"
    assert repository.events[-2:] == [("run", "failed"), "commit"]


def test_successful_state_and_succeeded_status_share_one_atomic_transaction():
    repository = _TransactionalRepository()
    with repository.transaction():
        start_drive_sync_run(
            repository, sync_run_id="run", root_folder_id=ROOT, started_at=STARTED
        )
    classifications = classify_drive_state(
        repository, root_folder_id=ROOT, inventory=[_file("new")]
    )
    with pytest.raises(RuntimeError, match="persistence failed"):
        with repository.transaction():
            repository.save_drive_file = Mock(side_effect=RuntimeError("persistence failed"))
            persist_successful_drive_state(
                repository,
                sync_run_id="run",
                root_folder_id=ROOT,
                started_at=STARTED,
                observed_at=OBSERVED,
                classifications=classifications,
            )
    assert repository.committed_runs["run"]["status"] == "running"
    assert repository.committed_files == {}
    assert repository.events[-1] == "rollback"


def test_empty_inventory_succeeds_without_drive_file_persistence():
    repository = _repo()
    classifications = classify_drive_state(
        repository, root_folder_id=ROOT, inventory=[]
    )
    result = persist_successful_drive_state(
        repository,
        sync_run_id="empty-run",
        root_folder_id=ROOT,
        started_at=STARTED,
        observed_at=OBSERVED,
        classifications=classifications,
    )
    assert result.classifications == ()
    repository.save_drive_file.assert_not_called()
    assert repository.save_drive_sync_run.call_args.args[0]["status"] == "succeeded"


def test_orchestration_does_not_download_ingest_or_mutate_content_state():
    adapter = Mock()
    repository = _repo()
    inventory = discover_drive_inventory(
        adapter,
        ROOT,
        discover=Mock(return_value=[_file("file")]),
    )
    classifications = classify_drive_state(
        repository, root_folder_id=ROOT, inventory=inventory
    )
    persist_successful_drive_state(
        repository,
        sync_run_id="run",
        root_folder_id=ROOT,
        started_at=STARTED,
        observed_at=OBSERVED,
        classifications=classifications,
    )
    adapter.download_file.assert_not_called()
    assert not hasattr(repository, "save_source")
    assert not hasattr(repository, "save_evidence")
    assert not hasattr(repository, "save_record")
    assert not hasattr(repository, "save_normalized_dataset")


def test_persistence_failure_rolls_back_explicitly_without_partial_state():
    repository = _TransactionalRepository()
    with repository.transaction():
        start_drive_sync_run(
            repository, sync_run_id="run", root_folder_id=ROOT, started_at=STARTED
        )
    classifications = classify_drive_state(
        repository, root_folder_id=ROOT, inventory=[_file("new")]
    )
    repository.save_drive_file = Mock(
        side_effect=RuntimeError("persistence failed")
    )
    with pytest.raises(RuntimeError, match="persistence failed"):
        with repository.transaction():
            persist_successful_drive_state(
                repository,
                sync_run_id="run",
                root_folder_id=ROOT,
                started_at=STARTED,
                observed_at=OBSERVED,
                classifications=classifications,
            )
    assert repository.events[-1] == "rollback"
    assert repository.committed_files == {}
    assert repository.committed_runs["run"]["status"] == "running"


def test_new_modified_unchanged_and_deleted_semantics():
    indexed = datetime(2026, 10, 6, 10, tzinfo=timezone.utc)
    repository = _repo(
        [
            PreviousDriveFileState(ROOT, "same", indexed, "sha256:same", indexed),
            PreviousDriveFileState(ROOT, "changed", indexed, "sha256:changed", indexed),
            PreviousDriveFileState(ROOT, "gone", None),
        ]
    )
    inventory = [_file("changed", "2026-10-06T11:00:00Z"), _file("same")]
    classifications = classify_drive_state(
        repository, root_folder_id=ROOT, inventory=inventory
    )
    assert [item.classification for item in classifications] == [
        DriveSyncClassification.MODIFIED,
        DriveSyncClassification.DELETED,
        DriveSyncClassification.UNCHANGED,
    ]
    result = persist_successful_drive_state(
        repository,
        sync_run_id="run",
        root_folder_id=ROOT,
        started_at=STARTED,
        observed_at=OBSERVED,
        classifications=classifications,
    )
    assert result.classifications == tuple(classifications)
    saved = {
        call.args[0]["drive_file_id"]: call.args[0]
        for call in repository.save_drive_file.call_args_list
    }
    assert set(saved) == {"changed", "same"}
    assert saved["changed"]["source_id"] == "sha256:changed"
    assert saved["changed"]["indexed_modified_time"] == indexed
    assert saved["changed"]["last_indexed_at"] == indexed
    assert repository.save_drive_sync_run.call_args.args[0]["status"] == "succeeded"


def test_root_isolation_and_deterministic_ordering():
    repository = _repo([PreviousDriveFileState("other", "other-file", None)])
    classifications = classify_drive_state(
        repository,
        root_folder_id=ROOT,
        inventory=[_file("z"), _file("a")],
    )
    assert [item.drive_file_id for item in classifications] == ["a", "z"]
    assert all(
        item.classification is DriveSyncClassification.NEW for item in classifications
    )


def test_repository_methods_do_not_own_transactions_or_connection():
    repository = _repo()
    start_drive_sync_run(
        repository, sync_run_id="run", root_folder_id=ROOT, started_at=STARTED
    )
    assert not hasattr(repository, "commit")
    assert not hasattr(repository, "rollback")
    assert not hasattr(repository, "close")
