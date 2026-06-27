using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace windowsAssistant.UI.Services;

public class ApiClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public ApiClient(string baseUrl = "http://localhost:8000")
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromMinutes(5),
        };
    }

    public async Task<TResponse> PostJsonAsync<TResponse>(string path, object payload)
    {
        var json = JsonSerializer.Serialize(payload);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");

        try
        {
            using var response = await _httpClient.PostAsync($"{_baseUrl}{path}", content);
            var responseBody = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                throw new ApiException($"Request to {_baseUrl}{path} failed with {(int)response.StatusCode}: {responseBody}");
            }

            return JsonSerializer.Deserialize<TResponse>(responseBody, JsonOptions)
                ?? throw new ApiException("The API returned an empty response.");
        }
        catch (HttpRequestException ex)
        {
            throw new ApiException($"Could not reach the backend at {_baseUrl}. Is it running? ({ex.Message})", ex);
        }
        catch (TaskCanceledException ex)
        {
            throw new ApiException("The backend request timed out.", ex);
        }
    }
}

public class ApiException : Exception
{
    public ApiException(string message) : base(message) { }
    public ApiException(string message, Exception inner) : base(message, inner) { }
}
