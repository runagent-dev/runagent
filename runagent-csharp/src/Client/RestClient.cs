using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using RunAgent.Errors;
using RunAgent.Types;
using RunAgent.Utils;

namespace RunAgent.Client;

/// <summary>
/// REST client for HTTP-based RunAgent API interactions
/// </summary>
public class RestClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private readonly string? _apiKey;
    private readonly bool _isLocal;

    public RestClient(string baseUrl, string? apiKey, bool isLocal)
    {
        _baseUrl = baseUrl;
        _apiKey = apiKey;
        _isLocal = isLocal;

        // Configure HttpClient with proper timeout and connection settings
        var handler = new SocketsHttpHandler
        {
            PooledConnectionLifetime = TimeSpan.FromMinutes(2),
            PooledConnectionIdleTimeout = TimeSpan.FromMinutes(1),
            ConnectTimeout = TimeSpan.FromSeconds(15)
        };

        _httpClient = new HttpClient(handler)
        {
            Timeout = TimeSpan.FromSeconds(Constants.DefaultTimeoutSeconds + 10)
        };

        // Set User-Agent header
        _httpClient.DefaultRequestHeaders.UserAgent.Add(
            new ProductInfoHeaderValue("RunAgent-CSharp", "0.1.49")
        );

        // Set Authorization header for remote calls
        if (!_isLocal && !string.IsNullOrEmpty(_apiKey))
        {
            _httpClient.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue("Bearer", _apiKey);
        }
    }

    /// <summary>
    /// Fetch agent architecture and entrypoints
    /// </summary>
    public async Task<AgentArchitecture> GetAgentArchitecture(string agentId)
    {
        var url = $"{_baseUrl}{Constants.ApiPrefix}/agents/{agentId}/architecture";

        try
        {
            // Add timeout specifically for this request
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            var response = await _httpClient.GetAsync(url, cts.Token);
            var content = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                HandleHttpError(response.StatusCode, content);
            }

            // Try to parse as envelope first
            try
            {
                var envelope = JsonSerializer.Deserialize<ApiResponse<AgentArchitecture>>(content);
                if (envelope?.Success == true && envelope.Data != null)
                {
                    return envelope.Data;
                }
                else if (envelope?.Success == false && envelope.Error != null)
                {
                    throw new RunAgentExecutionError(
                        envelope.Error.Code,
                        envelope.Error.Message,
                        envelope.Error.Suggestion,
                        envelope.Error.Details
                    );
                }
            }
            catch (JsonException)
            {
                // Try parsing as direct payload
                var architecture = JsonSerializer.Deserialize<AgentArchitecture>(content);
                if (architecture != null)
                {
                    return architecture;
                }
            }

            throw new ValidationError("Failed to parse agent architecture response");
        }
        catch (HttpRequestException ex)
        {
            throw new ConnectionError($"Failed to fetch agent architecture: {ex.Message}", ex);
        }
        catch (TaskCanceledException)
        {
            throw new ConnectionError("Request timed out while fetching agent architecture");
        }
    }

    /// <summary>
    /// Execute agent via REST API
    /// </summary>
    public async Task<object?> RunAgent(
        string agentId,
        string entrypointTag,
        List<object>? inputArgs = null,
        Dictionary<string, object>? inputKwargs = null,
        int timeoutSeconds = Constants.DefaultTimeoutSeconds,
        string? userId = null,
        bool persistentMemory = false
    )
    {
        var url = $"{_baseUrl}{Constants.ApiPrefix}/agents/{agentId}/run";

        var payload = new Dictionary<string, object>
        {
            ["entrypoint_tag"] = entrypointTag,
            ["input_args"] = inputArgs ?? new List<object>(),
            ["input_kwargs"] = inputKwargs ?? new Dictionary<string, object>(),
            ["timeout_seconds"] = timeoutSeconds,
            ["async_execution"] = false
        };

        // Add persistent memory parameters if provided
        if (!string.IsNullOrEmpty(userId))
        {
            payload["user_id"] = userId;
        }
        if (persistentMemory)
        {
            payload["persistent_memory"] = persistentMemory;
        }

        var jsonContent = JsonSerializer.Serialize(payload);
        var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

        try
        {
            var response = await _httpClient.PostAsync(url, content);
            var responseContent = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                HandleHttpError(response.StatusCode, responseContent);
            }

            return ParseRunResponse(responseContent);
        }
        catch (HttpRequestException ex)
        {
            throw new ConnectionError($"Failed to execute agent: {ex.Message}", ex);
        }
        catch (TaskCanceledException)
        {
            throw new ConnectionError("Request timed out during agent execution");
        }
    }

    /// <summary>
    /// Health check for agent availability
    /// </summary>
    public async Task<bool> HealthCheck()
    {
        var url = $"{_baseUrl}{Constants.ApiPrefix}/health";

        try
        {
            var response = await _httpClient.GetAsync(url);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// Parse run response and extract result data
    /// </summary>
    private object? ParseRunResponse(string responseContent)
    {
        try
        {
            var envelope = JsonSerializer.Deserialize<ApiResponse<JsonElement>>(responseContent);

            if (envelope?.Success == false && envelope.Error != null)
            {
                throw new RunAgentExecutionError(
                    envelope.Error.Code,
                    envelope.Error.Message,
                    envelope.Error.Suggestion,
                    envelope.Error.Details
                );
            }

            if (envelope?.Success == true && envelope.Data.ValueKind != JsonValueKind.Undefined && envelope.Data.ValueKind != JsonValueKind.Null)
            {
                var data = envelope.Data;

                // Check if data is a string (JSON-encoded string from local server)
                if (data.ValueKind == JsonValueKind.String)
                {
                    var dataString = data.GetString();
                    if (!string.IsNullOrEmpty(dataString))
                    {
                        // Parse the JSON string
                        return JsonSerializer.Deserialize<object>(dataString);
                    }
                }

                // Try to extract result_data.data (legacy structured output)
                if (data.TryGetProperty("result_data", out var resultData) &&
                    resultData.TryGetProperty("data", out var innerData))
                {
                    return JsonSerializer.Deserialize<object>(innerData.GetRawText());
                }

                // Return data directly
                return JsonSerializer.Deserialize<object>(data.GetRawText());
            }

            // Fallback: try to parse as direct JSON
            return JsonSerializer.Deserialize<object>(responseContent);
        }
        catch (JsonException ex)
        {
            throw new ValidationError($"Failed to parse response: {ex.Message}");
        }
    }

    /// <summary>
    /// Handle HTTP errors and throw appropriate exceptions
    /// </summary>
    private void HandleHttpError(HttpStatusCode statusCode, string content)
    {
        // Try to parse structured error
        try
        {
            var envelope = JsonSerializer.Deserialize<ApiResponse<object>>(content);
            if (envelope?.Error != null)
            {
                var error = envelope.Error;
                var exception = new RunAgentExecutionError(
                    error.Code,
                    error.Message,
                    error.Suggestion,
                    error.Details
                );

                // Map to specific error types based on code
                if (error.Code.Contains("AUTHENTICATION") || statusCode == HttpStatusCode.Unauthorized)
                    throw new AuthenticationError(exception.Message);
                if (error.Code.Contains("PERMISSION") || statusCode == HttpStatusCode.Forbidden)
                    throw new PermissionError(exception.Message);
                if (error.Code.Contains("VALIDATION") || error.Code.Contains("NOT_FOUND"))
                    throw new ValidationError(exception.Message);
                if (error.Code.Contains("SERVER") || error.Code.Contains("INTERNAL"))
                    throw new ServerError(exception.Message);

                throw exception;
            }
        }
        catch (JsonException)
        {
            // Fallback to status code mapping
        }

        // Map HTTP status codes to error types
        var message = $"HTTP {(int)statusCode}: {content}";

        switch (statusCode)
        {
            case HttpStatusCode.Unauthorized:
                throw new AuthenticationError("Authentication failed. Please provide a valid API key via RUNAGENT_API_KEY environment variable or constructor.");
            case HttpStatusCode.Forbidden:
                throw new PermissionError("Access denied. Check your API key permissions.");
            case HttpStatusCode.BadRequest:
            case HttpStatusCode.NotFound:
            case HttpStatusCode.UnprocessableEntity:
                throw new ValidationError(message);
            case HttpStatusCode.InternalServerError:
            case HttpStatusCode.BadGateway:
            case HttpStatusCode.ServiceUnavailable:
            case HttpStatusCode.GatewayTimeout:
                throw new ServerError(message);
            default:
                throw new UnknownError(message);
        }
    }

    public void Dispose()
    {
        _httpClient?.Dispose();
    }
}
