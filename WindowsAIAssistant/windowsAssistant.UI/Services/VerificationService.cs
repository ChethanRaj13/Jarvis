using System.Collections.Generic;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class VerificationService
{
    private readonly ApiClient _apiClient = new();

    public async Task<string> VerifyAsync(List<string> steps, string targetResource = ".")
    {
        if (steps == null)
        {
            steps = new List<string>();
        }

        var response = await _apiClient.PostJsonAsync<VerificationApiResponse>("/verify", new
        {
            steps,
            target_resource = targetResource,
            action_type = "FILE_CREATE",
            risk_level = "low"
        });

        return response?.Summary ?? "Verification completed.";
    }
}

public class VerificationApiResponse
{
    [JsonPropertyName("final_decision")]
    public string? FinalDecision { get; set; }

    [JsonPropertyName("full_rationale")]
    public string? FullRationale { get; set; }

    [JsonPropertyName("summary")]
    public string? Summary { get; set; }
}