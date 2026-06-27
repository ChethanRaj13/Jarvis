using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Contracts;

public interface ILifecycleManager
{
    Task<TaskItem> CreateAsync(TaskItem item);
    Task<TaskItem?> GetAsync(string taskId);
    Task UpdateStatusAsync(string taskId, windowsAssistant.UI.Models.TaskStatus status);
}
