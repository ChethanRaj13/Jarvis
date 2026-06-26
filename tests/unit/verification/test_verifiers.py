from datetime import datetime, timezone
from uuid import uuid4

from verification_engine.contracts import (
    ActionType,
    AuthorizationRecord,
    EvidencePackage,
    EvidenceType,
    RiskLevel,
    VerificationDecisionEnum,
)
from verification_engine.verification.configuration import ConfigurationVerifier
from verification_engine.verification.download import DownloadVerifier
from verification_engine.verification.filesystem import FilesystemVerifier
from verification_engine.verification.process import ProcessVerifier
from verification_engine.verification.registry import RegistryVerifier
from verification_engine.verification.task import TaskVerifier


UTC_NOW = datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def authorization(
    *,
    request_id=None,
    action_type=ActionType.FILE_CREATE,
    target_resource="C:/Temp/example.txt",
    scope=None,
) -> AuthorizationRecord:
    return AuthorizationRecord(
        authorization_id="auth-1",
        request_id=request_id or uuid4(),
        action_type=action_type,
        target_resource=target_resource,
        authorized_scope=scope or {"exists": True},
        risk_level=RiskLevel.MEDIUM,
        authorization_timestamp=UTC_NOW,
        expected_outcome_specification={"ok": True},
    )


def evidence(request_id, evidence_type, payload) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=uuid4(),
        request_id=request_id,
        evidence_type=evidence_type,
        collection_timestamp=UTC_NOW,
        collection_window_open=True,
        binding_token="binding-token",
        collector_id="collector",
        evidence_payload=payload,
    )


def filesystem_payload(**overrides):
    payload = {
        "file_path": "C:\\Temp\\example.txt",
        "exists": True,
        "file_size_bytes": 10,
        "sha256_hash": HASH,
        "creation_timestamp_utc": UTC_NOW.isoformat(),
        "last_modified_timestamp_utc": UTC_NOW.isoformat(),
        "file_attributes": {"archive": True},
        "owner_sid": "S-1",
        "dacl_summary": {"entries": []},
    }
    payload.update(overrides)
    return payload


def test_filesystem_verifier_verified_and_failed():
    auth = authorization(
        scope={
            "exists": True,
            "file_size_bytes": 10,
            "sha256_hash": HASH,
            "owner_sid": "S-1",
        }
    )

    verified = FilesystemVerifier().verify(auth, evidence(auth.request_id, EvidenceType.FILESYSTEM, filesystem_payload()))
    failed = FilesystemVerifier().verify(
        auth,
        evidence(auth.request_id, EvidenceType.FILESYSTEM, filesystem_payload(file_size_bytes=9)),
    )

    assert verified.sub_decision == VerificationDecisionEnum.VERIFIED
    assert failed.sub_decision == VerificationDecisionEnum.FAILED
    assert "file_size_bytes" in failed.failed_attributes


def test_filesystem_verifier_partial_for_unexpected_entries():
    auth = authorization(scope={"exists": True})
    result = FilesystemVerifier().verify(
        auth,
        evidence(
            auth.request_id,
            EvidenceType.FILESYSTEM,
            filesystem_payload(unexpected_files=["C:\\Temp\\extra.txt"]),
        ),
    )

    assert result.sub_decision == VerificationDecisionEnum.PARTIAL
    assert "unexpected_filesystem_entries" in result.failed_attributes


def test_verifier_escalates_for_wrong_evidence_type():
    auth = authorization(scope={"exists": True})
    result = FilesystemVerifier().verify(auth, evidence(auth.request_id, EvidenceType.REGISTRY, {"key_path": "HKCU\\x"}))

    assert result.sub_decision == VerificationDecisionEnum.ESCALATE


def test_registry_verifier_verified_failed_and_partial():
    auth = authorization(
        action_type=ActionType.REGISTRY_MODIFY,
        target_resource="HKCU\\Software\\Example",
        scope={"key_exists": True, "value_name": "Name", "value_type": "REG_SZ", "value_data": "ok"},
    )
    payload = {
        "key_path": "HKCU\\Software\\Example",
        "key_exists": True,
        "value_name": "Name",
        "value_type": "REG_SZ",
        "value_data": "ok",
        "is_in_protected_hive": False,
    }

    assert RegistryVerifier().verify(auth, evidence(auth.request_id, EvidenceType.REGISTRY, payload)).sub_decision == VerificationDecisionEnum.VERIFIED
    failed_payload = dict(payload, value_type="REG_EXPAND_SZ")
    assert RegistryVerifier().verify(auth, evidence(auth.request_id, EvidenceType.REGISTRY, failed_payload)).sub_decision == VerificationDecisionEnum.FAILED
    partial_payload = dict(payload, adjacent_key_modifications=["HKCU\\Software\\Other"])
    assert RegistryVerifier().verify(auth, evidence(auth.request_id, EvidenceType.REGISTRY, partial_payload)).sub_decision == VerificationDecisionEnum.PARTIAL


def test_registry_verifier_fails_protected_hive_without_authorization():
    auth = authorization(
        action_type=ActionType.REGISTRY_MODIFY,
        target_resource="HKLM\\SYSTEM\\Example",
        scope={"key_exists": True},
    )
    payload = {
        "key_path": "HKLM\\SYSTEM\\Example",
        "key_exists": True,
        "is_in_protected_hive": True,
    }

    result = RegistryVerifier().verify(auth, evidence(auth.request_id, EvidenceType.REGISTRY, payload))

    assert result.sub_decision == VerificationDecisionEnum.FAILED
    assert "protected_hive" in result.failed_attributes


def test_process_verifier_verified_failed_and_partial():
    auth = authorization(
        action_type=ActionType.PROCESS_LAUNCH,
        target_resource="C:/Tools/tool.exe",
        scope={"process_exists": True, "integrity_level": "Medium", "command_line_parameters": ["--run"]},
    )
    payload = {
        "executable_path": "C:\\Tools\\tool.exe",
        "process_exists": True,
        "integrity_level": "Medium",
        "command_line_parameters": ["--run"],
        "child_processes": [],
    }

    assert ProcessVerifier().verify(auth, evidence(auth.request_id, EvidenceType.PROCESS, payload)).sub_decision == VerificationDecisionEnum.VERIFIED
    assert ProcessVerifier().verify(auth, evidence(auth.request_id, EvidenceType.PROCESS, dict(payload, integrity_level="High"))).sub_decision == VerificationDecisionEnum.FAILED
    assert ProcessVerifier().verify(auth, evidence(auth.request_id, EvidenceType.PROCESS, dict(payload, child_processes=[{"pid": 2}]))).sub_decision == VerificationDecisionEnum.PARTIAL


def test_task_verifier_verified_failed_partial_and_persistence_failure():
    auth = authorization(
        action_type=ActionType.TASK_CREATE,
        target_resource="\\Example\\Task",
        scope={
            "task_exists": True,
            "executable_path": "C:/Tools/task.exe",
            "run_as_user": "User",
            "highest_run_level": False,
            "triggers": [{"type": "daily"}],
        },
    )
    payload = {
        "task_name": "\\Example\\Task",
        "task_exists": True,
        "executable_path": "C:\\Tools\\task.exe",
        "run_as_user": "User",
        "highest_run_level": False,
        "triggers": [{"type": "daily"}],
    }

    assert TaskVerifier().verify(auth, evidence(auth.request_id, EvidenceType.TASK, payload)).sub_decision == VerificationDecisionEnum.VERIFIED
    assert TaskVerifier().verify(auth, evidence(auth.request_id, EvidenceType.TASK, dict(payload, triggers=[{"type": "weekly"}]))).sub_decision == VerificationDecisionEnum.FAILED
    assert TaskVerifier().verify(auth, evidence(auth.request_id, EvidenceType.TASK, dict(payload, adjacent_tasks_created=["\\Other"]))).sub_decision == VerificationDecisionEnum.PARTIAL
    assert TaskVerifier().verify(auth, evidence(auth.request_id, EvidenceType.TASK, dict(payload, unauthorized_persistence_entries=["RunKey"]))).sub_decision == VerificationDecisionEnum.FAILED


def test_download_verifier_verified_failed_partial_and_escalate():
    auth = authorization(
        action_type=ActionType.DOWNLOAD,
        target_resource="C:/Downloads/file.pdf",
        scope={"sha256_hash": HASH, "declared_file_type": "application/pdf", "file_exists": True},
    )
    payload = {
        "file_path": "C:\\Downloads\\file.pdf",
        "file_exists": True,
        "sha256_hash": HASH,
        "detected_file_type": "application/pdf",
        "type_mismatch": False,
        "has_been_executed": False,
        "additional_write_paths": [],
    }

    assert DownloadVerifier().verify(auth, evidence(auth.request_id, EvidenceType.DOWNLOAD, payload)).sub_decision == VerificationDecisionEnum.VERIFIED
    assert DownloadVerifier().verify(auth, evidence(auth.request_id, EvidenceType.DOWNLOAD, dict(payload, has_been_executed=True))).sub_decision == VerificationDecisionEnum.FAILED
    assert DownloadVerifier().verify(auth, evidence(auth.request_id, EvidenceType.DOWNLOAD, dict(payload, additional_write_paths=["C:\\Other\\file.pdf"]))).sub_decision == VerificationDecisionEnum.PARTIAL
    no_hash_auth = authorization(action_type=ActionType.DOWNLOAD, target_resource="C:/Downloads/file.pdf", scope={"declared_file_type": "application/pdf"})
    assert DownloadVerifier().verify(no_hash_auth, evidence(no_hash_auth.request_id, EvidenceType.DOWNLOAD, payload)).sub_decision == VerificationDecisionEnum.ESCALATE


def test_configuration_verifier_verified_failed_partial_and_safety_guard():
    auth = authorization(
        action_type=ActionType.CONFIG_MODIFY,
        target_resource="C:/Configs/verification.json",
        scope={"config_format": "JSON", "expected_values": {"enabled": True}},
    )
    payload = {
        "config_source_type": "FILE",
        "config_path": "C:\\Configs\\verification.json",
        "config_format": "JSON",
        "all_key_value_pairs": {"enabled": True},
        "is_safety_engine_config": False,
    }

    assert ConfigurationVerifier().verify(auth, evidence(auth.request_id, EvidenceType.CONFIGURATION, payload)).sub_decision == VerificationDecisionEnum.VERIFIED
    assert ConfigurationVerifier().verify(auth, evidence(auth.request_id, EvidenceType.CONFIGURATION, dict(payload, all_key_value_pairs={"enabled": False}))).sub_decision == VerificationDecisionEnum.FAILED
    assert ConfigurationVerifier().verify(auth, evidence(auth.request_id, EvidenceType.CONFIGURATION, dict(payload, unauthorized_changes=["extra"]))).sub_decision == VerificationDecisionEnum.PARTIAL
    guarded_payload = dict(payload, is_safety_engine_config=True, unauthorized_changes=["extra"])
    assert ConfigurationVerifier().verify(auth, evidence(auth.request_id, EvidenceType.CONFIGURATION, guarded_payload)).sub_decision == VerificationDecisionEnum.FAILED


def test_invalid_authorization_escalates_without_business_logic():
    auth = AuthorizationRecord.model_construct(
        authorization_id="bad",
        request_id=uuid4(),
        action_type=ActionType.FILE_CREATE,
        target_resource="C:/Temp/example.txt",
        authorized_scope={},
        risk_level=RiskLevel.MEDIUM,
        authorization_timestamp=UTC_NOW,
        expected_outcome_specification={},
    )

    result = FilesystemVerifier().verify(auth, evidence(auth.request_id, EvidenceType.FILESYSTEM, filesystem_payload()))

    assert result.sub_decision == VerificationDecisionEnum.ESCALATE
