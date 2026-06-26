namespace windowsAssistant.UI.Services;

public class AutomationService : IAutomationService
{
    public Task ExecuteAsync(string instruction, CancellationToken cancellationToken = default)
    {
        // TODO: Add desktop automation implementation.
        return Task.CompletedTask;
    }
}
