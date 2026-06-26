namespace windowsAssistant.UI.Services;

public interface IAutomationService
{
    Task ExecuteAsync(string instruction, CancellationToken cancellationToken = default);
}
