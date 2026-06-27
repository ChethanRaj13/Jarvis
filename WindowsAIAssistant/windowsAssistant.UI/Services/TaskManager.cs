using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using windowsAssistant.UI.Contracts;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class TaskManager : ITaskManager
{
    private readonly ITaskCoordinator _coordinator;
    private readonly ILifecycleManager _lifecycle;
    private readonly IRuntimeStateStore _state;
    private readonly ExecutionEngine _executionEngine;

    public TaskManager(
        ITaskCoordinator coordinator,
        ILifecycleManager lifecycle,
        IRuntimeStateStore state,
        ExecutionEngine executionEngine)
    {
        _coordinator = coordinator;
        _lifecycle = lifecycle;
        _state = state;
        _executionEngine = executionEngine;
    }

    public async Task<TaskItem> CreateTaskAsync(TaskExecutionPlan plan, TaskContext? context = null)
    {
        var item = new TaskItem
        {
            Title = "Generated Task",
            Description = "Plan received from planner",
            Plan = plan,
            Context = context
        };

        await _coordinator.SendPlanAsync(plan, context);
        return item;
    }

    public async Task<List<string>> ExecuteTaskAsync(TaskItem item)
    {
        if (item == null || item.Plan == null)
        {
            return new List<string> { "Invalid task or plan." };
        }

        await _lifecycle.UpdateStatusAsync(item.TaskId, windowsAssistant.UI.Models.TaskStatus.Running);
        await _state.SaveStateAsync(item);

        var logs = await _executionEngine.ExecutePlanAsync(item.Plan);

        var status = logs.Exists(l => l.Contains("failed")) ? windowsAssistant.UI.Models.TaskStatus.Failed : windowsAssistant.UI.Models.TaskStatus.Completed;
        await _lifecycle.UpdateStatusAsync(item.TaskId, status);
        await _state.SaveStateAsync(item);

        return logs;
    }

    public Task<string> VerifyTaskAsync(TaskItem item, string targetResource = ".")
    {
        if (item == null || item.Plan == null)
        {
            return Task.FromResult("Invalid task or plan.");
        }

        return _executionEngine.VerifyPlanAsync(item.Plan, targetResource);
    }

    public async Task<IEnumerable<TaskItem>> GetActiveTasksAsync()
    {
        // For simplicity, load all known tasks from the store (not persisted to disk yet)
        // This runtime store is in-memory so we can't enumerate; return placeholder empty list
        return Enumerable.Empty<TaskItem>();
    }

    public Task PauseTaskAsync(string taskId) => _lifecycle.UpdateStatusAsync(taskId, windowsAssistant.UI.Models.TaskStatus.Paused);
    public Task ResumeTaskAsync(string taskId) => _lifecycle.UpdateStatusAsync(taskId, windowsAssistant.UI.Models.TaskStatus.Queued);
    public Task CancelTaskAsync(string taskId) => _lifecycle.UpdateStatusAsync(taskId, windowsAssistant.UI.Models.TaskStatus.Cancelled);
    public Task<TaskItem?> GetTaskAsync(string taskId) => _lifecycle.GetAsync(taskId);
}
