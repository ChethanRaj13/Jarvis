from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from WindowsAIAssistant.backend.verification_engine.contracts import ActionType, AuthorizationRecord, EvidenceType, VerificationRequest
from WindowsAIAssistant.backend.verification_engine.evidence.collectors import (
    CollectionRequest,
    ConfigurationCollector,
    DownloadCollector,
    FilesystemCollector,
    ProcessCollector,
    RegistryCollector,
    TaskCollector,
)
from WindowsAIAssistant.backend.verification_engine.evidence.validation import ValidationContext, ValidationService
from WindowsAIAssistant.backend.verification_engine.integrations import (
    CompletionReportingAdapter,
    ExecutionLayerTriggerAdapter,
    SafetyEngineAuthorizationAdapter,
)
from WindowsAIAssistant.backend.verification_engine.orchestrator import ExecutionContext, VerificationOrchestrator
from WindowsAIAssistant.backend.verification_engine.verification import (
    ConfigurationVerifier,
    DownloadVerifier,
    FilesystemVerifier,
    ProcessVerifier,
    RegistryVerifier,
    TaskVerifier,
)

from .trigger import VerificationTriggerService


_ACTION_WIRING: dict[ActionType, tuple[EvidenceType, Any, Any]] = {
    ActionType.FILE_CREATE: (EvidenceType.FILESYSTEM, FilesystemCollector, FilesystemVerifier),
    ActionType.FILE_DELETE: (EvidenceType.FILESYSTEM, FilesystemCollector, FilesystemVerifier),
    ActionType.FILE_MODIFY: (EvidenceType.FILESYSTEM, FilesystemCollector, FilesystemVerifier),
    ActionType.FILE_MOVE: (EvidenceType.FILESYSTEM, FilesystemCollector, FilesystemVerifier),
    ActionType.REGISTRY_CREATE: (EvidenceType.REGISTRY, RegistryCollector, RegistryVerifier),
    ActionType.REGISTRY_MODIFY: (EvidenceType.REGISTRY, RegistryCollector, RegistryVerifier),
    ActionType.REGISTRY_DELETE: (EvidenceType.REGISTRY, RegistryCollector, RegistryVerifier),
    ActionType.PROCESS_LAUNCH: (EvidenceType.PROCESS, ProcessCollector, ProcessVerifier),
    ActionType.PROCESS_TERMINATE: (EvidenceType.PROCESS, ProcessCollector, ProcessVerifier),
    ActionType.TASK_CREATE: (EvidenceType.TASK, TaskCollector, TaskVerifier),
    ActionType.TASK_MODIFY: (EvidenceType.TASK, TaskCollector, TaskVerifier),
    ActionType.TASK_DELETE: (EvidenceType.TASK, TaskCollector, TaskVerifier),
    ActionType.DOWNLOAD: (EvidenceType.DOWNLOAD, DownloadCollector, DownloadVerifier),
    ActionType.CONFIG_MODIFY: (EvidenceType.CONFIGURATION, ConfigurationCollector, ConfigurationVerifier),
}


def get_verification_service() -> VerificationTriggerService:
    return VerificationTriggerService(
        execution_adapter=ExecutionLayerTriggerAdapter(),
        safety_adapter=SafetyEngineAuthorizationAdapter(),
        completion_adapter=CompletionReportingAdapter(),
        context_factory=build_execution_context,
        orchestrator_factory=build_orchestrator,
    )


def build_execution_context(request: VerificationRequest, authorization: AuthorizationRecord) -> ExecutionContext:
    collection_requests = _build_collection_requests(request, authorization)
    return ExecutionContext(
        request=request,
        authorization=authorization,
        collection_requests=collection_requests,
        validation_context=ValidationContext(
            request_id=request.request_id,
            execution_timestamp=request.execution_timestamp,
            evidence_window_seconds=30,
        ),
        execution_metadata={"detection_scope": authorization.target_resource},
    )


def build_orchestrator(context: ExecutionContext) -> VerificationOrchestrator:
    if not context.collection_requests:
        return VerificationOrchestrator(validation_service=ValidationService())
    collectors = []
    verifiers = []
    for collection_request in context.collection_requests:
        _, collector_type, verifier_type = _ACTION_WIRING[context.request.action_type]
        if collection_request.evidence_type != _ACTION_WIRING[context.request.action_type][0]:
            continue
        collectors.append(collector_type())
        verifiers.append(verifier_type())
    return VerificationOrchestrator(
        collectors=tuple(collectors),
        validation_service=ValidationService(),
        verifiers=tuple(verifiers),
    )


def _build_collection_requests(
    request: VerificationRequest,
    authorization: AuthorizationRecord,
) -> tuple[CollectionRequest, ...]:
    raw_evidence = authorization.expected_outcome_specification.get("raw_evidence")
    if raw_evidence is None:
        return ()

    evidence_type = _ACTION_WIRING[request.action_type][0]
    now = datetime.now(timezone.utc)
    return (
        CollectionRequest(
            request_id=request.request_id,
            evidence_type=evidence_type,
            raw_evidence=raw_evidence,
            collection_timestamp=now,
            collection_window_open=True,
            binding_token=f"binding-{request.request_id}",
            collector_id=f"{evidence_type.value.lower()}-collector",
            evidence_id=uuid4(),
        ),
    )
