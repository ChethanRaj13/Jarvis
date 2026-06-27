using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class ToolMetadata
{
    [JsonPropertyName("risk_level")] public string RiskLevel { get; set; } = "low";
    [JsonPropertyName("timeout_seconds")] public int TimeoutSeconds { get; set; } = 60;
    [JsonPropertyName("requires_admin")] public bool RequiresAdmin { get; set; }
    [JsonPropertyName("verification_support")] public bool VerificationSupport { get; set; }
    [JsonPropertyName("supported_capabilities")] public List<string> SupportedCapabilities { get; set; } = new();
    [JsonPropertyName("supported_actions")] public List<string> SupportedActions { get; set; } = new();
}
