class DecisionError(Exception):
    """Base exception for decision engine failures."""


class InvalidDecisionInput(DecisionError):
    """Raised when decision inputs are invalid or incomplete."""


class DecisionAggregationError(DecisionError):
    """Raised when decision aggregation cannot complete safely."""


class PrecedenceResolutionError(DecisionError):
    """Raised when precedence cannot be resolved safely."""


class EscalationError(DecisionError):
    """Raised when escalation handling cannot complete safely."""
