using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
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

    public async Task<CalendarParseResponse> ParseCalendarFieldsAsync(string text)
    {
        try
        {
            var response = await _apiClient.PostJsonAsync<CalendarParseResponse>("/parse-calendar", new { text });
            return NormalizeCalendarResponse(response, text);
        }
        catch (ApiException)
        {
            return ParseCalendarFieldsLocally(text);
        }
    }

    public CalendarParseResponse ParseCalendarFieldsLocally(string text)
    {
        var normalized = text?.Trim() ?? string.Empty;
        var parsedDate = TryExtractDateTime(normalized, out var eventDateTime);
        var title = ExtractTitle(normalized);

        return new CalendarParseResponse
        {
            Date = parsedDate ? eventDateTime.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : string.Empty,
            Time = parsedDate ? eventDateTime.ToString("h:mm tt", CultureInfo.InvariantCulture) : string.Empty,
            Message = string.IsNullOrWhiteSpace(title) ? "Calendar event" : title,
            Description = normalized,
        };
    }

    private CalendarParseResponse NormalizeCalendarResponse(CalendarParseResponse response, string fallbackText)
    {
        if (response == null ||
            string.IsNullOrWhiteSpace(response.Date) ||
            string.IsNullOrWhiteSpace(response.Time) ||
            string.IsNullOrWhiteSpace(response.Message))
        {
            return ParseCalendarFieldsLocally(fallbackText);
        }

        return response;
    }

    private static bool TryExtractDateTime(string text, out DateTime eventDateTime)
    {
        eventDateTime = DateTime.MinValue;
        if (string.IsNullOrWhiteSpace(text))
        {
            return false;
        }

        var normalized = text.Trim();
        var explicitPatterns = new[]
        {
            @"\b(?<value>\d{4}-\d{1,2}-\d{1,2}(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:[APap][Mm])?)?)\b",
            @"\b(?<value>\d{1,2}/\d{1,2}/\d{2,4}(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:[APap][Mm])?)?)\b",
            @"\bon\s+(?<value>\w+ \d{1,2}(?:st|nd|rd|th)?(?:, \d{4})?(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:[APap][Mm])?)?)",
        };

        foreach (var pattern in explicitPatterns)
        {
            var match = Regex.Match(normalized, pattern, RegexOptions.IgnoreCase);
            if (match.Success && DateTime.TryParse(CleanDateSuffixes(match.Groups["value"].Value), CultureInfo.CurrentCulture, DateTimeStyles.None, out eventDateTime))
            {
                return true;
            }
        }

        var relativeDate = DateTime.Today;
        if (Regex.IsMatch(normalized, @"\btomorrow\b", RegexOptions.IgnoreCase))
        {
            relativeDate = DateTime.Today.AddDays(1);
        }
        else if (!Regex.IsMatch(normalized, @"\btoday\b", RegexOptions.IgnoreCase))
        {
            return false;
        }

        var timeMatch = Regex.Match(normalized, @"\b(?:at\s+)?(?<time>\d{1,2}(?::\d{2})?\s*(?:[APap][Mm]))\b", RegexOptions.IgnoreCase);
        if (timeMatch.Success && DateTime.TryParse(timeMatch.Groups["time"].Value, CultureInfo.CurrentCulture, DateTimeStyles.NoCurrentDateDefault, out var parsedTime))
        {
            eventDateTime = relativeDate.Date.Add(parsedTime.TimeOfDay);
            return true;
        }

        eventDateTime = relativeDate.Date.AddHours(9);
        return true;
    }

    private static string CleanDateSuffixes(string value)
    {
        return Regex.Replace(value, @"\b(\d{1,2})(st|nd|rd|th)\b", "$1", RegexOptions.IgnoreCase);
    }

    private static string ExtractTitle(string text)
    {
        var normalized = text.Trim();
        var quoted = Regex.Match(normalized, "\"(?<title>[^\"]+)\"");
        if (quoted.Success)
        {
            return quoted.Groups["title"].Value.Trim();
        }

        var called = Regex.Match(normalized, @"\b(?:called|named|title(?:d)?|about)\s+(?<title>.+?)(?:\s+(?:on|at|tomorrow|today)\b|$)", RegexOptions.IgnoreCase);
        if (called.Success)
        {
            return called.Groups["title"].Value.Trim(' ', '.', ',');
        }

        var cleaned = Regex.Replace(normalized, @"\b(?:add|create|schedule|set|make)\b", "", RegexOptions.IgnoreCase);
        cleaned = Regex.Replace(cleaned, @"\b(?:a|an|the)?\s*(?:calendar\s+)?(?:event|meeting|appointment|reminder)\b", "", RegexOptions.IgnoreCase);
        cleaned = Regex.Replace(cleaned, @"\b(?:on|at)\s+.*$", "", RegexOptions.IgnoreCase);
        cleaned = Regex.Replace(cleaned, @"\b(?:today|tomorrow)\b.*$", "", RegexOptions.IgnoreCase);
        return cleaned.Trim(' ', '.', ',');
    }
}

public class CalendarParseResponse
{
    [JsonPropertyName("date")]
    public string Date { get; set; } = string.Empty;

    [JsonPropertyName("time")]
    public string Time { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;
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
