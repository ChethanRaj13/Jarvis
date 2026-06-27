using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class TaskStep
{
    [JsonPropertyName("step_number")] public int StepNumber { get; set; }
    [JsonPropertyName("action")] public string Action { get; set; } = string.Empty;
    [JsonPropertyName("command")] public string? Command { get; set; }
    [JsonPropertyName("capability_id")] public string? CapabilityId { get; set; }
    [JsonPropertyName("tool_id")] public string? ToolId { get; set; }
    [JsonPropertyName("is_completed")] public bool IsCompleted { get; set; }
}
