namespace windowsAssistant.UI.Models;

public class VerificationResult
{
    public string CheckName { get; set; } = "";

    public bool Passed { get; set; }

    public string Message { get; set; } = "";
}