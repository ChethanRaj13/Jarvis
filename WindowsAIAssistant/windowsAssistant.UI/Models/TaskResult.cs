using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class TaskResult
{
    [JsonPropertyName("success")] public bool Success { get; set; }
    [JsonPropertyName("message")] public string Message { get; set; } = string.Empty;
}
