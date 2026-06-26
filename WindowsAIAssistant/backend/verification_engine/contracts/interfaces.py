from abc import ABC, abstractmethod
from uuid import UUID

from .schemas import (
    AuthorizationRecord,
    AuthorizationRetrievalRequest,
    EvidencePackage,
    EvidenceReference,
    ExecutionCompletionSignal,
    VerificationOutcomeMessage,
    VerificationRecord,
    VerificationRequest,
    WriteConfirmation,
)


class IExecutionLayerTriggerAdapter(ABC):
    @abstractmethod
    def receive_signal(self, signal: ExecutionCompletionSignal) -> VerificationRequest | None:
        """Validate an Execution Layer trigger and return a verification request or discard it."""


class ISafetyEngineAuthorizationAdapter(ABC):
    @abstractmethod
    def retrieve_authorization(self, request: AuthorizationRetrievalRequest) -> AuthorizationRecord:
        """Retrieve and validate the Safety Engine authorization record for a request."""


class ICompletionReportingAdapter(ABC):
    @abstractmethod
    def deliver_outcome(self, message: VerificationOutcomeMessage) -> None:
        """Deliver the audited verification outcome to Completion Reporting."""


class IEvidenceStore(ABC):
    @abstractmethod
    def get_evidence(self, evidence_id: UUID) -> EvidencePackage:
        """Return a stored evidence package by identifier."""

    @abstractmethod
    def resolve_reference(self, evidence_id: UUID) -> EvidenceReference:
        """Return a lightweight evidence reference for audit embedding."""


class IAuditWriter(ABC):
    @abstractmethod
    def write_record(self, record: VerificationRecord) -> WriteConfirmation:
        """Append a verification record and return the audit write confirmation."""
