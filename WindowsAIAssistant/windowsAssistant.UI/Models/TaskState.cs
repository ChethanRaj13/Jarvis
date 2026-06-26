namespace windowsAssistant.UI.Models;

public enum TaskState
{
    Created,
    Planned,
    Queued,
    Executing,
    Verifying,
    Completed,
    Failed,
    Cancelled,
    Paused,
    Retrying,
    Timeout
}
