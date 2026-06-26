namespace windowsAssistant.UI.Services;

public class ExecutionService
{
    public List<string> Execute(List<string> steps)
    {
        List<string> executionLogs = new();

        foreach (var step in steps)
        {
            executionLogs.Add($"Executing: {step}");
        }

        executionLogs.Add("Execution Completed");

        return executionLogs;
    }
}