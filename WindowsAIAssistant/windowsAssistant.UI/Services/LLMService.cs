namespace windowsAssistant.UI.Services;

public class LLMService : ILLMService
{
    public Task<string> GenerateAsync(string prompt, CancellationToken cancellationToken = default)
    {
        // TODO: Connect to the selected LLM provider.
        return Task.FromResult(string.Empty);
    }
}
