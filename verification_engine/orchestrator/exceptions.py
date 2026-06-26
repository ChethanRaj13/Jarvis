class OrchestratorError(Exception):
    """Base exception for orchestrator failures."""


class PipelineError(OrchestratorError):
    """Raised when pipeline execution fails closed."""


class InvalidStateTransition(OrchestratorError):
    """Raised when an illegal lifecycle state transition is attempted."""


class OrchestrationFailure(OrchestratorError):
    """Raised when the verification lifecycle cannot complete safely."""
