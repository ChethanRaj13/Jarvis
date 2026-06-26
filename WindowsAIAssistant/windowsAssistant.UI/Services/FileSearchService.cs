namespace windowsAssistant.UI.Services;

public class FileSearchService : IFileSearchService
{
    public Task<IEnumerable<string>> SearchAsync(string query, CancellationToken cancellationToken = default)
    {
        // TODO: Add file search implementation.
        return Task.FromResult(Enumerable.Empty<string>());
    }
}
