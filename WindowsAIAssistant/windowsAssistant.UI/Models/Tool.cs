using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class Tool
{
    [JsonPropertyName("tool_id")] public string ToolId { get; set; } = string.Empty;
    [JsonPropertyName("tool_name")] public string ToolName { get; set; } = string.Empty;
    [JsonPropertyName("category")] public string Category { get; set; } = string.Empty;
    [JsonPropertyName("capabilities")] public List<Capability> Capabilities { get; set; } = new();
    [JsonPropertyName("metadata")] public ToolMetadata Metadata { get; set; } = new();
    [JsonPropertyName("status")] public string Status { get; set; } = "unknown";
}
