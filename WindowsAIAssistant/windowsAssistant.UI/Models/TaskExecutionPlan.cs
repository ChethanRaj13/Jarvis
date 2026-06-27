using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class TaskExecutionPlan
{
    [JsonPropertyName("plan_id")] public string PlanId { get; set; } = System.Guid.NewGuid().ToString();
    [JsonPropertyName("steps")] public List<TaskStep> Steps { get; set; } = new();
}
