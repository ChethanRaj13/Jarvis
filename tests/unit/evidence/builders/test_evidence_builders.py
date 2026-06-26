from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from verification_engine.contracts import EvidencePackage, EvidenceType
from verification_engine.evidence.builders import (
    ConfigurationEvidenceBuilder,
    DownloadEvidenceBuilder,
    EvidenceBuilderValidationError,
    FilesystemEvidenceBuilder,
    ProcessEvidenceBuilder,
    RegistryEvidenceBuilder,
    TaskEvidenceBuilder,
)


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def build_kwargs() -> dict:
    return {
        "request_id": uuid4(),
        "collection_timestamp": UTC_NOW,
        "collection_window_open": True,
        "binding_token": "binding-token",
        "collector_id": "collector",
        "collection_duration_ms": 5,
    }


def test_filesystem_builder_valid_build():
    package = FilesystemEvidenceBuilder().build(
        {
            "file_path": "C:/Temp/example.txt",
            "exists": True,
            "file_size_bytes": 10,
            "sha256_hash": HASH,
            "creation_timestamp_utc": UTC_NOW,
            "last_modified_timestamp_utc": UTC_NOW,
            "file_attributes": {"archive": True},
            "owner_sid": "S-1",
            "dacl_summary": {"entries": []},
        },
        **build_kwargs(),
    )

    assert isinstance(package, EvidencePackage)
    assert package.evidence_type == EvidenceType.FILESYSTEM
    assert package.evidence_payload["file_path"] == "C:\\Temp\\example.txt"

    with pytest.raises(ValidationError):
        package.collector_id = "changed"


def test_filesystem_builder_missing_attributes_raises_typed_exception():
    with pytest.raises(EvidenceBuilderValidationError):
        FilesystemEvidenceBuilder().build(
            {
                "file_path": "C:/Temp/example.txt",
                "exists": True,
            },
            **build_kwargs(),
        )


def test_registry_builder_valid_build():
    package = RegistryEvidenceBuilder().build(
        {
            "key_path": "hkey_local_machine/software/example",
            "key_exists": True,
            "value_name": "Name",
            "value_type": "REG_SZ",
            "value_data": "value",
            "key_last_written_timestamp": UTC_NOW,
            "subkey_names": ["Child"],
            "parent_key_last_written_timestamp": UTC_NOW,
            "is_in_protected_hive": False,
        },
        **build_kwargs(),
    )

    assert package.evidence_type == EvidenceType.REGISTRY
    assert package.evidence_payload["key_path"] == "HKLM\\software\\example"


def test_registry_builder_invalid_data_raises_typed_exception():
    with pytest.raises(EvidenceBuilderValidationError):
        RegistryEvidenceBuilder().build(
            {
                "key_path": "Software\\Example",
                "key_exists": True,
                "value_name": "Name",
                "value_type": "SZ",
                "value_data": "value",
                "key_last_written_timestamp": UTC_NOW,
                "subkey_names": [],
                "parent_key_last_written_timestamp": UTC_NOW,
                "is_in_protected_hive": False,
            },
            **build_kwargs(),
        )


def test_process_builder_valid_build():
    package = ProcessEvidenceBuilder().build(
        {
            "process_id": 123,
            "process_name": "tool.exe",
            "executable_path": "C:/Tools/tool.exe",
            "command_line_parameters": ("--flag",),
            "parent_process_id": 1,
            "session_id": "session-1",
            "integrity_level": "Medium",
            "token_elevation_type": "Default",
            "process_creation_timestamp": UTC_NOW,
            "child_processes": ({"process_id": 124},),
            "process_exists": True,
        },
        **build_kwargs(),
    )

    assert package.evidence_type == EvidenceType.PROCESS
    assert package.evidence_payload["executable_path"] == "C:\\Tools\\tool.exe"
    assert package.evidence_payload["command_line_parameters"] == ["--flag"]


def test_task_builder_valid_build():
    package = TaskEvidenceBuilder().build(
        {
            "task_name": "\\Example\\Task",
            "task_exists": True,
            "executable_path": "C:/Tools/task.exe",
            "arguments": ("--run",),
            "working_directory": "C:/Tools",
            "run_as_user": "User",
            "highest_run_level": False,
            "triggers": ({"type": "daily"},),
            "task_state": "Ready",
            "creation_date": UTC_NOW,
            "last_run_time": UTC_NOW,
            "adjacent_tasks": ["\\Example\\Other"],
        },
        **build_kwargs(),
    )

    assert package.evidence_type == EvidenceType.TASK
    assert package.evidence_payload["arguments"] == ["--run"]
    assert package.evidence_payload["triggers"] == [{"type": "daily"}]


def test_download_builder_valid_build_with_optional_metadata_absent():
    package = DownloadEvidenceBuilder().build(
        {
            "file_path": "C:/Downloads/file.pdf",
            "file_exists": True,
            "sha256_hash": HASH,
            "file_size_bytes": 100,
            "detected_file_type": "application/pdf",
            "declared_file_type": "application/pdf",
            "type_mismatch": False,
            "has_been_executed": False,
            "additional_write_paths": ("C:/Downloads/file.pdf",),
        },
        **build_kwargs(),
    )

    assert package.evidence_type == EvidenceType.DOWNLOAD
    assert package.evidence_payload["file_path"] == "C:\\Downloads\\file.pdf"
    assert "execution_flag_in_filesystem" in package.evidence_payload
    assert package.evidence_payload["execution_flag_in_filesystem"] is None


def test_download_builder_invalid_hash_raises_typed_exception():
    with pytest.raises(EvidenceBuilderValidationError):
        DownloadEvidenceBuilder().build(
            {
                "file_path": "C:/Downloads/file.pdf",
                "file_exists": True,
                "sha256_hash": "not-a-sha256",
                "file_size_bytes": 100,
                "detected_file_type": "application/pdf",
                "declared_file_type": "application/pdf",
                "type_mismatch": False,
                "has_been_executed": False,
                "additional_write_paths": [],
            },
            **build_kwargs(),
        )


def test_configuration_builder_valid_build():
    package = ConfigurationEvidenceBuilder().build(
        {
            "config_source_type": "file",
            "config_path": "C:/Configs/verification.json",
            "config_format": "json",
            "all_key_value_pairs": {"enabled": True},
            "last_modified_timestamp": UTC_NOW,
            "is_safety_engine_config": False,
            "is_policy_enforcement_config": True,
            "file_hash": HASH,
            "parsed_at_timestamp": UTC_NOW,
        },
        **build_kwargs(),
    )

    assert package.evidence_type == EvidenceType.CONFIGURATION
    assert package.evidence_payload["config_source_type"] == "FILE"
    assert package.evidence_payload["config_path"] == "C:\\Configs\\verification.json"
    assert package.evidence_payload["config_format"] == "JSON"
