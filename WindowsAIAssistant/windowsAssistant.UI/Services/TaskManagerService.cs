using System.Collections.ObjectModel;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public class TaskManagerService : ITaskManagerService
{
    public ObservableCollection<AgentTask> Tasks { get; } = new();

    public AgentTask CreateTask(string title = "", string description = "")
    {
        // TODO: Queue new agent tasks when task creation flow is implemented.
        var task = new AgentTask
        {
            Title = title,
            Description = description,
            CreatedAt = DateTime.Now,
            UpdatedAt = DateTime.Now
        };

        Tasks.Add(task);
        return task;
    }

    public void UpdateTask(AgentTask task)
    {
        // TODO: Update task state and notify persistence/agents.
        task.UpdatedAt = DateTime.Now;
    }

    public void RemoveTask(AgentTask task)
    {
        // TODO: Coordinate removal with persistence when implemented.
        Tasks.Remove(task);
    }

    public void PauseTask(AgentTask task)
    {
        // TODO: Pause running executor work.
        task.State = TaskState.Paused;
        task.UpdatedAt = DateTime.Now;
    }

    public void ResumeTask(AgentTask task)
    {
        // TODO: Resume paused executor work.
        task.State = TaskState.Queued;
        task.UpdatedAt = DateTime.Now;
    }

    public void CancelTask(AgentTask task)
    {
        // TODO: Cancel running executor work.
        task.State = TaskState.Cancelled;
        task.UpdatedAt = DateTime.Now;
    }

    public void RetryTask(AgentTask task)
    {
        // TODO: Retry failed task execution.
        task.State = TaskState.Retrying;
        task.UpdatedAt = DateTime.Now;
    }

    public ObservableCollection<AgentTask> GetAllTasks()
    {
        // TODO: Return persisted tasks when storage is implemented.
        return Tasks;
    }

    public AgentTask? GetTaskById(Guid id)
    {
        // TODO: Query persisted task store when storage is implemented.
        return Tasks.FirstOrDefault(task => task.Id == id);
    }
}
