using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class Entity
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("value")]
    public string Value { get; set; } = string.Empty;
}

public class StructuredIntent
{
    [JsonPropertyName("raw_text")]
    public string RawText { get; set; } = string.Empty;

    [JsonPropertyName("normalized_text")]
    public string NormalizedText { get; set; } = string.Empty;

    [JsonPropertyName("intent_type")]
    public string IntentType { get; set; } = string.Empty;

    [JsonPropertyName("confidence")]
    public double Confidence { get; set; }

    [JsonPropertyName("entities")]
    public List<Entity> Entities { get; set; } = new();

    [JsonPropertyName("risk_level")]
    public string RiskLevel { get; set; } = string.Empty;

    [JsonPropertyName("risk_reasons")]
    public List<string> RiskReasons { get; set; } = new();
}

public class PlanStep
{
    [JsonPropertyName("step_number")]
    public int StepNumber { get; set; }

    [JsonPropertyName("action")]
    public string Action { get; set; } = string.Empty;

    [JsonPropertyName("tool_or_method")]
    public string? ToolOrMethod { get; set; }
}

public class SubGoalPlan
{
    [JsonPropertyName("sub_goal_id")]
    public string SubGoalId { get; set; } = string.Empty;

    [JsonPropertyName("sub_goal_description")]
    public string SubGoalDescription { get; set; } = string.Empty;

    [JsonPropertyName("depends_on")]
    public List<string> DependsOn { get; set; } = new();

    [JsonPropertyName("steps")]
    public List<PlanStep> Steps { get; set; } = new();
}

public class TaskPlan
{
    [JsonPropertyName("original_intent")]
    public StructuredIntent OriginalIntent { get; set; } = new();

    [JsonPropertyName("sub_goal_plans")]
    public List<SubGoalPlan> SubGoalPlans { get; set; } = new();
}

/// <summary>
/// Combined response from POST /plan: the parsed intent plus the resulting task plan.
/// </summary>
public class PlanResponse
{
    [JsonPropertyName("intent")]
    public StructuredIntent Intent { get; set; } = new();

    [JsonPropertyName("plan")]
    public TaskPlan Plan { get; set; } = new();
}

/// <summary>
/// Thin HTTP client around the FastAPI Intent Parser / Task Planner service
/// (api.py / POST /parse and POST /plan).
/// </summary>
public class IntentApiClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public IntentApiClient(string baseUrl = "http://localhost:8000", HttpClient? httpClient = null)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _httpClient = httpClient ?? new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(30),
        };
    }

    /// <summary>
    /// Sends the raw user message to the FastAPI /parse endpoint and returns
    /// the structured intent only (no plan). Throws IntentApiException on any
    /// failure so the caller can decide how to surface it in the UI.
    /// </summary>
    public Task<StructuredIntent> ParseAsync(string userMessage)
        => PostAsync<StructuredIntent>("/parse", userMessage);

    /// <summary>
    /// Sends the raw user message to the FastAPI /plan endpoint, which runs
    /// the full pipeline (IntentParser -> TaskPlanner) and returns both the
    /// resulting intent and the task plan in one round trip.
    /// </summary>
    public Task<PlanResponse> PlanAsync(string userMessage)
        => PostAsync<PlanResponse>("/plan", userMessage);

    private async Task<T> PostAsync<T>(string path, string userMessage)
    {
        var payload = new { text = userMessage };
        var json = JsonSerializer.Serialize(payload);

        using var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpResponseMessage response;
        try
        {
            response = await _httpClient.PostAsync($"{_baseUrl}{path}", content);
        }
        catch (HttpRequestException ex)
        {
            throw new IntentApiException(
                $"Could not reach the intent service at {_baseUrl}. Is it running? ({ex.Message})", ex);
        }
        catch (TaskCanceledException ex)
        {
            throw new IntentApiException("The intent service took too long to respond.", ex);
        }

        var responseBody = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            string detail = TryExtractDetail(responseBody) ?? responseBody;
            throw new IntentApiException(
                $"Intent service returned {(int)response.StatusCode}: {detail}");
        }

        try
        {
            var result = JsonSerializer.Deserialize<T>(responseBody, JsonOptions);
            if (result is null)
                throw new IntentApiException("Intent service returned an empty response.");

            return result;
        }
        catch (JsonException ex)
        {
            throw new IntentApiException("Could not parse the intent service response.", ex);
        }
    }

    private static string? TryExtractDetail(string responseBody)
    {
        try
        {
            using var doc = JsonDocument.Parse(responseBody);
            if (doc.RootElement.TryGetProperty("detail", out var detail))
                return detail.ToString();
        }
        catch (JsonException)
        {
            // Body wasn't JSON — fall back to returning the raw body upstream.
        }

        return null;
    }
}

public class IntentApiException : Exception
{
    public IntentApiException(string message) : base(message) { }
    public IntentApiException(string message, Exception inner) : base(message, inner) { }
}