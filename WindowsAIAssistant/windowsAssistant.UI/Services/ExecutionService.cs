using System.Collections.Generic;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class ExecutionService
{
    private readonly ApiClient _apiClient = new();

    public async Task<ExecutionApiResponse> GenerateExecutionPlanAsync(List<string> steps)
    {
        if (steps == null)
        {
            steps = new List<string>();
        }

        var response = await _apiClient.PostJsonAsync<ExecutionApiResponse>("/execute", new { steps, verify = false });
        return response ?? new ExecutionApiResponse();
    }
}

public class ExecutionApiResponse
{
    [JsonPropertyName("logs")]
    public List<string> Logs { get; set; } = new();

    [JsonPropertyName("commands")]
    public List<ExecutionCommand> Commands { get; set; } = new();

    [JsonPropertyName("verification")]
    public object? Verification { get; set; }
}

public class ExecutionCommand
{
    [JsonPropertyName("command")]
    public string Command { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("tool")]
    public string? Tool { get; set; }
}