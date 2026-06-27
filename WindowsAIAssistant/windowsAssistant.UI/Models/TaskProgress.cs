using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class TaskProgress
{
    [JsonPropertyName("current_step")] public int CurrentStep { get; set; }
    [JsonPropertyName("total_steps")] public int TotalSteps { get; set; }
}
