namespace windowsAssistant.UI.Infrastructure.AI;

public class EmbeddingService
{
    public Task<float[]> CreateEmbeddingAsync(string input, CancellationToken cancellationToken = default)
    {
        // TODO: Add embedding generation.
        return Task.FromResult(Array.Empty<float>());
    }
}
