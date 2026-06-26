namespace windowsAssistant.UI.Models;

public class TaskExecution
{
    public string Command { get; set; } = "";

    public List<ExecutionStep> Steps { get; set; } = new();

    public TaskState State { get; set; } = new();
}