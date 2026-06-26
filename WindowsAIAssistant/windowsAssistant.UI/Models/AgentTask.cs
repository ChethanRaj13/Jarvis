using System.Collections.ObjectModel;

namespace windowsAssistant.UI.Models;

public class AgentTask
{
    public Guid Id { get; set; } = Guid.NewGuid();

    public string Title { get; set; } = string.Empty;

    public string Description { get; set; } = string.Empty;

    public string CurrentStep { get; set; } = string.Empty;

    public int Progress { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.Now;

    public DateTime UpdatedAt { get; set; } = DateTime.Now;

    public TaskPriority Priority { get; set; } = TaskPriority.Medium;

    public TaskState State { get; set; } = TaskState.Created;

    public string AssignedAgent { get; set; } = string.Empty;

    public bool RequiresVerification { get; set; }

    public bool RequiresApproval { get; set; }

    public ObservableCollection<string> Logs { get; set; } = new();

    public ObservableCollection<string> Steps { get; set; } = new();
}
