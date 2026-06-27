using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Contracts;

public interface IRuntimeStateStore
{
    Task SaveStateAsync(TaskItem item);
    Task<TaskItem?> LoadStateAsync(string taskId);
}
