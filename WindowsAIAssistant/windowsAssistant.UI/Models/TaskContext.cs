using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class TaskContext
{
    [JsonPropertyName("user_id")] public string? UserId { get; set; }
    [JsonPropertyName("metadata")] public Dictionary<string, string> Metadata { get; set; } = new();
}
