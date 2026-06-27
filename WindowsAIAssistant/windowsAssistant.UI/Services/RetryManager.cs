using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class RetryManager
{
    public Task<bool> ShouldRetryAsync(string taskId) => Task.FromResult(false);
}
