using System.Text.Json.Serialization;

namespace windowsAssistant.UI.Models;

public class Capability
{
    [JsonPropertyName("capability_id")]
    public string CapabilityId { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;
}
