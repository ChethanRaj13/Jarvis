using System.Collections.ObjectModel;
using windowsAssistant.UI.Models;

namespace windowsAssistant.UI.Services;

public interface ITaskManagerService
{
    ObservableCollection<AgentTask> Tasks { get; }

    AgentTask CreateTask(string title = "", string description = "");

    void UpdateTask(AgentTask task);

    void RemoveTask(AgentTask task);

    void PauseTask(AgentTask task);

    void ResumeTask(AgentTask task);

    void CancelTask(AgentTask task);

    void RetryTask(AgentTask task);

    ObservableCollection<AgentTask> GetAllTasks();

    AgentTask? GetTaskById(Guid id);
}
