using System.Collections.Generic;
using System.Threading.Tasks;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Contracts;

public interface ITaskManager
{
    Task<TaskItem> CreateTaskAsync(TaskExecutionPlan plan, TaskContext? context = null);
    Task<IEnumerable<TaskItem>> GetActiveTasksAsync();
    Task PauseTaskAsync(string taskId);
    Task ResumeTaskAsync(string taskId);
    Task CancelTaskAsync(string taskId);
    Task<TaskItem?> GetTaskAsync(string taskId);
}
