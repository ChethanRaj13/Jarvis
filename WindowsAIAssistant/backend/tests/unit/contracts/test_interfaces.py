import pytest

from WindowsAIAssistant.backend.verification_engine.contracts.interfaces import (
    IAuditWriter,
    ICompletionReportingAdapter,
    IEvidenceStore,
    IExecutionLayerTriggerAdapter,
    ISafetyEngineAuthorizationAdapter,
)


@pytest.mark.parametrize(
    "interface",
    [
        IAuditWriter,
        ICompletionReportingAdapter,
        IEvidenceStore,
        IExecutionLayerTriggerAdapter,
        ISafetyEngineAuthorizationAdapter,
    ],
)
def test_interfaces_are_abstract(interface):
    with pytest.raises(TypeError):
        interface()


def test_concrete_interface_inheritance():
    class CompletionAdapter(ICompletionReportingAdapter):
        def deliver_outcome(self, message):
            self.message = message

    adapter = CompletionAdapter()
    assert isinstance(adapter, ICompletionReportingAdapter)
