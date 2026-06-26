namespace windowsAssistant.UI.Models;

public class TaskState
{
    public string TaskName { get; set; } = "";

    public string Status { get; set; } = "";

    public int Progress { get; set; }

    public string CurrentStep { get; set; } = "";
}