namespace windowsAssistant.UI.Services;

public interface ILLMService
{
    Task<string> GenerateAsync(string prompt, CancellationToken cancellationToken = default);
}
