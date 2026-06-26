from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

from verification_engine.contracts import EvidencePackage, EvidenceType
from verification_engine.evidence.collectors import (
    BaseCollector,
    CollectionFailure,
    CollectionRequest,
    ConfigurationCollector,
    DownloadCollector,
    FilesystemCollector,
    InvalidCollectionRequest,
    ProcessCollector,
    RegistryCollector,
    TaskCollector,
    UnsupportedCollection,
)


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def request_for(evidence_type: EvidenceType, raw_evidence: dict[str, Any]) -> CollectionRequest:
    return CollectionRequest(
        request_id=uuid4(),
        evidence_type=evidence_type,
        raw_evidence=raw_evidence,
        collection_timestamp=UTC_NOW,
        collection_window_open=True,
        binding_token="binding-token",
        collector_id="collector",
        collection_duration_ms=3,
    )


def filesystem_raw() -> dict[str, Any]:
    return {
        "file_path": "C:/Temp/example.txt",
        "exists": True,
        "file_size_bytes": 10,
        "sha256_hash": HASH,
        "creation_timestamp_utc": UTC_NOW,
        "last_modified_timestamp_utc": UTC_NOW,
        "file_attributes": {"archive": True},
        "owner_sid": "S-1",
        "dacl_summary": {"entries": []},
    }


def registry_raw() -> dict[str, Any]:
    return {
        "key_path": "hkey_current_user/software/example",
        "key_exists": True,
        "value_name": "Name",
        "value_type": "REG_SZ",
        "value_data": "value",
        "key_last_written_timestamp": UTC_NOW,
        "subkey_names": ["Child"],
        "parent_key_last_written_timestamp": UTC_NOW,
        "is_in_protected_hive": False,
    }


def process_raw() -> dict[str, Any]:
    return {
        "process_id": 100,
        "process_name": "tool.exe",
        "executable_path": "C:/Tools/tool.exe",
        "command_line_parameters": ["--flag"],
        "parent_process_id": 1,
        "session_id": "session-1",
        "integrity_level": "Medium",
        "token_elevation_type": "Default",
        "process_creation_timestamp": UTC_NOW,
        "child_processes": [],
        "process_exists": True,
    }


def task_raw() -> dict[str, Any]:
    return {
        "task_name": "\\Example\\Task",
        "task_exists": True,
        "executable_path": "C:/Tools/task.exe",
        "arguments": ["--run"],
        "working_directory": "C:/Tools",
        "run_as_user": "User",
        "highest_run_level": False,
        "triggers": [{"type": "daily"}],
        "task_state": "Ready",
        "creation_date": UTC_NOW,
        "last_run_time": UTC_NOW,
        "adjacent_tasks": [],
    }


def download_raw() -> dict[str, Any]:
    return {
        "file_path": "C:/Downloads/file.pdf",
        "file_exists": True,
        "sha256_hash": HASH,
        "file_size_bytes": 100,
        "detected_file_type": "application/pdf",
        "declared_file_type": "application/pdf",
        "type_mismatch": False,
        "has_been_executed": False,
        "additional_write_paths": [],
    }


def config_raw() -> dict[str, Any]:
    return {
        "config_source_type": "file",
        "config_path": "C:/Configs/verification.json",
        "config_format": "json",
        "all_key_value_pairs": {"enabled": True},
        "last_modified_timestamp": UTC_NOW,
        "is_safety_engine_config": False,
        "is_policy_enforcement_config": True,
    }


def test_filesystem_collector_collects_raw_evidence_and_invokes_builder():
    package = FilesystemCollector().collect(request_for(EvidenceType.FILESYSTEM, filesystem_raw()))

    assert isinstance(package, EvidencePackage)
    assert package.evidence_type == EvidenceType.FILESYSTEM
    assert package.evidence_payload["file_path"] == "C:\\Temp\\example.txt"
    assert package.evidence_payload["sha256_hash"] == HASH


def test_registry_collector_collects_registry_metadata():
    package = RegistryCollector().collect(request_for(EvidenceType.REGISTRY, registry_raw()))

    assert package.evidence_type == EvidenceType.REGISTRY
    assert package.evidence_payload["key_path"] == "HKCU\\software\\example"
    assert package.evidence_payload["value_type"] == "REG_SZ"


def test_process_collector_collects_process_metadata():
    package = ProcessCollector().collect(request_for(EvidenceType.PROCESS, process_raw()))

    assert package.evidence_type == EvidenceType.PROCESS
    assert package.evidence_payload["process_id"] == 100
    assert package.evidence_payload["process_exists"] is True


def test_task_collector_collects_task_configuration():
    package = TaskCollector().collect(request_for(EvidenceType.TASK, task_raw()))

    assert package.evidence_type == EvidenceType.TASK
    assert package.evidence_payload["task_name"] == "\\Example\\Task"
    assert package.evidence_payload["triggers"] == [{"type": "daily"}]


def test_download_collector_collects_supplied_hash_without_computing():
    package = DownloadCollector().collect(request_for(EvidenceType.DOWNLOAD, download_raw()))

    assert package.evidence_type == EvidenceType.DOWNLOAD
    assert package.evidence_payload["sha256_hash"] == HASH
    assert package.evidence_payload["detected_file_type"] == "application/pdf"


def test_configuration_collector_collects_configuration_snapshot():
    package = ConfigurationCollector().collect(request_for(EvidenceType.CONFIGURATION, config_raw()))

    assert package.evidence_type == EvidenceType.CONFIGURATION
    assert package.evidence_payload["config_source_type"] == "FILE"
    assert package.evidence_payload["all_key_value_pairs"] == {"enabled": True}


def test_base_collector_rejects_unsupported_collection_type():
    request = request_for(EvidenceType.REGISTRY, filesystem_raw())

    with pytest.raises(UnsupportedCollection):
        FilesystemCollector().collect(request)


def test_base_collector_rejects_invalid_request():
    request = request_for(EvidenceType.FILESYSTEM, {})

    with pytest.raises(InvalidCollectionRequest):
        FilesystemCollector().collect(request)


def test_collector_fails_closed_when_builder_rejects_raw_evidence():
    bad_raw = filesystem_raw()
    bad_raw.pop("file_size_bytes")

    with pytest.raises(CollectionFailure):
        FilesystemCollector().collect(request_for(EvidenceType.FILESYSTEM, bad_raw))


def test_base_collector_invokes_configured_builder():
    class FakeBuilder:
        def __init__(self) -> None:
            self.called_with = None

        def build(self, raw_evidence, **kwargs):
            self.called_with = (raw_evidence, kwargs)
            return EvidencePackage(
                evidence_id=uuid4(),
                request_id=kwargs["request_id"],
                evidence_type=EvidenceType.FILESYSTEM,
                collection_timestamp=kwargs["collection_timestamp"],
                collection_window_open=kwargs["collection_window_open"],
                binding_token=kwargs["binding_token"],
                collector_id=kwargs["collector_id"],
                evidence_payload={"ok": True},
            )

    class FakeCollector(BaseCollector):
        evidence_type = EvidenceType.FILESYSTEM

        def __init__(self, builder):
            self.builder = builder

    builder = FakeBuilder()
    package = FakeCollector(builder).collect(request_for(EvidenceType.FILESYSTEM, {"ok": True}))

    assert package.evidence_payload == {"ok": True}
    assert builder.called_with[0] == {"ok": True}
    assert builder.called_with[1]["binding_token"] == "binding-token"
