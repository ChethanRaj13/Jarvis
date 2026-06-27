using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class CancellationManager
{
    public Task CancelAsync(string taskId) => Task.CompletedTask;
}
