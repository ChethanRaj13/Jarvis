using System.Collections.Generic;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class ExecutionService
{
    private readonly ApiClient _apiClient = new();

    public async Task<List<string>> ExecuteAsync(List<string> steps)
    {
        if (steps == null)
        {
            steps = new List<string>();
        }

        var response = await _apiClient.PostJsonAsync<ExecutionApiResponse>("/execute", new { steps, verify = true });
        return response?.Logs ?? new List<string>();
    }
}

public class ExecutionApiResponse
{
    [JsonPropertyName("logs")]
    public List<string> Logs { get; set; } = new();

    [JsonPropertyName("verification")]
    public object? Verification { get; set; }
}