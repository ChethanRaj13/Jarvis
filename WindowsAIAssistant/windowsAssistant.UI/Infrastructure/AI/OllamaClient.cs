namespace windowsAssistant.UI.Infrastructure.AI;

public class OllamaClient
{
    public Task<string> GenerateAsync(string prompt, CancellationToken cancellationToken = default)
    {
        // TODO: Add Ollama client calls.
        return Task.FromResult(string.Empty);
    }
}
