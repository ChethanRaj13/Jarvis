using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Contracts;

public interface ITaskQueue
{
    Task EnqueueAsync(TaskItem item);
    Task<TaskItem?> DequeueAsync();
    Task<TaskItem?> PeekAsync();
}
