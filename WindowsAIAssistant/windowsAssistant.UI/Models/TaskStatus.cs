using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public enum TaskStatus
{
    Created,
    Queued,
    Running,
    WaitingVerification,
    Completed,
    Failed,
    Cancelled,
    Paused
}
