using System.Text.Json.Serialization;

namespace RunAgent.Types;

/// <summary>
/// Configuration for RunAgent client
/// </summary>
public class RunAgentClientConfig
{
    /// <summary>
    /// Agent identifier (required)
    /// </summary>
    [JsonPropertyName("agent_id")]
    public string AgentId { get; set; }

    /// <summary>
    /// Entrypoint tag to invoke (required)
    /// </summary>
    [JsonPropertyName("entrypoint_tag")]
    public string EntrypointTag { get; set; }

    /// <summary>
    /// Enable local mode for co-located agents (default: false)
    /// </summary>
    [JsonPropertyName("local")]
    public bool Local { get; set; } = false;

    /// <summary>
    /// Host for local agent (optional, overrides auto-discovery)
    /// </summary>
    [JsonPropertyName("host")]
    public string? Host { get; set; }

    /// <summary>
    /// Port for local agent (optional, overrides auto-discovery)
    /// </summary>
    [JsonPropertyName("port")]
    public int? Port { get; set; }

    /// <summary>
    /// API key for remote authentication (optional, overrides environment)
    /// </summary>
    [JsonPropertyName("api_key")]
    public string? ApiKey { get; set; }

    /// <summary>
    /// Base URL for remote deployments (optional, overrides environment)
    /// </summary>
    [JsonPropertyName("base_url")]
    public string? BaseUrl { get; set; }

    /// <summary>
    /// User identifier for persistent memory isolation (optional)
    /// </summary>
    [JsonPropertyName("user_id")]
    public string? UserId { get; set; }

    /// <summary>
    /// Enable persistent memory across executions (default: false)
    /// </summary>
    [JsonPropertyName("persistent_memory")]
    public bool PersistentMemory { get; set; } = false;

    /// <summary>
    /// Extra parameters for future metadata use (optional)
    /// </summary>
    [JsonPropertyName("extra_params")]
    public Dictionary<string, object>? ExtraParams { get; set; }

    public RunAgentClientConfig(string agentId, string entrypointTag)
    {
        AgentId = agentId ?? throw new ArgumentNullException(nameof(agentId));
        EntrypointTag = entrypointTag ?? throw new ArgumentNullException(nameof(entrypointTag));
    }

    /// <summary>
    /// Factory method for fluent configuration
    /// </summary>
    public static RunAgentClientConfig Create(string agentId, string entrypointTag)
    {
        return new RunAgentClientConfig(agentId, entrypointTag);
    }

    /// <summary>
    /// Set local mode
    /// </summary>
    public RunAgentClientConfig WithLocal(bool local)
    {
        Local = local;
        return this;
    }

    /// <summary>
    /// Set host and port for local agent
    /// </summary>
    public RunAgentClientConfig WithHostAndPort(string host, int port)
    {
        Host = host;
        Port = port;
        return this;
    }

    /// <summary>
    /// Set API key for remote authentication
    /// </summary>
    public RunAgentClientConfig WithApiKey(string apiKey)
    {
        ApiKey = apiKey;
        return this;
    }

    /// <summary>
    /// Set base URL for remote deployments
    /// </summary>
    public RunAgentClientConfig WithBaseUrl(string baseUrl)
    {
        BaseUrl = baseUrl;
        return this;
    }

    /// <summary>
    /// Set user ID for persistent memory isolation
    /// </summary>
    public RunAgentClientConfig WithUserId(string userId)
    {
        UserId = userId;
        return this;
    }

    /// <summary>
    /// Enable persistent memory
    /// </summary>
    public RunAgentClientConfig WithPersistentMemory(bool persistentMemory)
    {
        PersistentMemory = persistentMemory;
        return this;
    }

    /// <summary>
    /// Set extra parameters
    /// </summary>
    public RunAgentClientConfig WithExtraParams(Dictionary<string, object> extraParams)
    {
        ExtraParams = extraParams;
        return this;
    }
}

/// <summary>
/// Agent architecture definition
/// </summary>
public class AgentArchitecture
{
    [JsonPropertyName("agent_id")]
    public string? AgentId { get; set; }

    [JsonPropertyName("entrypoints")]
    public List<EntryPoint>? Entrypoints { get; set; }
}

/// <summary>
/// Entrypoint definition for agent functions
/// </summary>
public class EntryPoint
{
    [JsonPropertyName("tag")]
    public string Tag { get; set; } = string.Empty;

    [JsonPropertyName("file")]
    public string? File { get; set; }

    [JsonPropertyName("module")]
    public string? Module { get; set; }

    [JsonPropertyName("extractor")]
    public object? Extractor { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }
}

/// <summary>
/// API response envelope
/// </summary>
public class ApiResponse<T>
{
    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("data")]
    public T? Data { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("error")]
    public ErrorInfo? Error { get; set; }

    [JsonPropertyName("timestamp")]
    public string? Timestamp { get; set; }

    [JsonPropertyName("request_id")]
    public string? RequestId { get; set; }
}

/// <summary>
/// Error information in API responses
/// </summary>
public class ErrorInfo
{
    [JsonPropertyName("code")]
    public string Code { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("suggestion")]
    public string? Suggestion { get; set; }

    [JsonPropertyName("details")]
    public string? Details { get; set; }
}
