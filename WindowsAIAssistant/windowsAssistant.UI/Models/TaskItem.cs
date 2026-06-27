using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class TaskItem
{
    [JsonPropertyName("task_id")] public string TaskId { get; set; } = Guid.NewGuid().ToString();
    [JsonPropertyName("title")] public string Title { get; set; } = string.Empty;
    [JsonPropertyName("description")] public string Description { get; set; } = string.Empty;
    [JsonPropertyName("priority")] public TaskPriority Priority { get; set; } = TaskPriority.Medium;
    [JsonPropertyName("status")] public TaskStatus Status { get; set; } = TaskStatus.Created;
    [JsonPropertyName("created_at")] public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    [JsonPropertyName("context")] public TaskContext? Context { get; set; }
    [JsonPropertyName("plan")] public TaskExecutionPlan? Plan { get; set; }
}
