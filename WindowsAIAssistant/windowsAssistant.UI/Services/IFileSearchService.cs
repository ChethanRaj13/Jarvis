namespace windowsAssistant.UI.Services;

public interface IFileSearchService
{
    Task<IEnumerable<string>> SearchAsync(string query, CancellationToken cancellationToken = default);
}
