namespace windowsAssistant.UI.Models;

public class ExecutionStep
{
    public int StepNumber { get; set; }

    public string Title { get; set; } = "";

    public bool IsCompleted { get; set; }

    public bool IsRunning { get; set; }
}