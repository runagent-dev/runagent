using RunAgent.Errors;
using RunAgent.Types;
using RunAgent.Utils;

namespace RunAgent.Client;

/// <summary>
/// Main client for interacting with RunAgent deployments
/// Supports both local and remote agents with streaming and non-streaming execution
/// </summary>
public class RunAgentClient : IDisposable
{
    private readonly RunAgentClientConfig _config;
    private readonly RestClient _restClient;
    private readonly SocketClient _socketClient;
    private readonly string _agentId;
    private readonly string _entrypointTag;
    private readonly bool _isLocal;
    private readonly string? _userId;
    private readonly bool _persistentMemory;
    private readonly Dictionary<string, object>? _extraParams;

    private AgentArchitecture? _architecture;
    private EntryPoint? _selectedEntrypoint;

    private RunAgentClient(RunAgentClientConfig config)
    {
        _config = config ?? throw new ArgumentNullException(nameof(config));
        _agentId = config.AgentId;
        _entrypointTag = config.EntrypointTag;
        _isLocal = config.Local;
        _userId = config.UserId;
        _persistentMemory = config.PersistentMemory;
        _extraParams = config.ExtraParams;

        // Resolve configuration
        var apiKey = ConfigLoader.ResolveApiKey(config.ApiKey);
        var baseUrl = ConfigLoader.ResolveBaseUrl(config.BaseUrl);
        var host = ConfigLoader.ResolveHost(config.Host);
        var port = ConfigLoader.ResolvePort(config.Port);

        // Build base URL
        string finalBaseUrl;
        if (_isLocal)
        {
            finalBaseUrl = $"http://{host}:{port}";
        }
        else
        {
            finalBaseUrl = baseUrl;

            // Validate API key for remote calls
            if (string.IsNullOrEmpty(apiKey))
            {
                throw new AuthenticationError(
                    "API key is required for remote agents. " +
                    "Set RUNAGENT_API_KEY environment variable or pass apiKey in config."
                );
            }
        }

        _restClient = new RestClient(finalBaseUrl, apiKey, _isLocal);
        _socketClient = new SocketClient(finalBaseUrl, apiKey, _isLocal);
    }

    /// <summary>
    /// Create and initialize a new RunAgentClient
    /// </summary>
    public static async Task<RunAgentClient> CreateAsync(RunAgentClientConfig config)
    {
        var client = new RunAgentClient(config);
        await client.InitializeAsync();
        return client;
    }

    /// <summary>
    /// Create a client from environment variables
    /// </summary>
    public static async Task<RunAgentClient> CreateFromEnvironmentAsync(
        string agentId,
        string entrypointTag
    )
    {
        var config = ConfigLoader.FromEnvironment(agentId, entrypointTag);
        return await CreateAsync(config);
    }

    /// <summary>
    /// Initialize client by fetching agent architecture and validating entrypoint
    /// </summary>
    private async Task InitializeAsync()
    {
        try
        {
            _architecture = await _restClient.GetAgentArchitecture(_agentId);

            if (_architecture?.Entrypoints == null || _architecture.Entrypoints.Count == 0)
            {
                throw new ValidationError(
                    "ARCHITECTURE_MISSING: Agent has no entrypoints defined. " +
                    "Please redeploy the agent with proper entrypoint configuration."
                );
            }

            // Find the requested entrypoint
            _selectedEntrypoint = _architecture.Entrypoints
                .FirstOrDefault(ep => ep.Tag == _entrypointTag);

            if (_selectedEntrypoint == null)
            {
                var availableTags = string.Join(", ", _architecture.Entrypoints.Select(ep => ep.Tag));
                throw new ValidationError(
                    $"Entrypoint '{_entrypointTag}' not found. " +
                    $"Available entrypoints: {availableTags}"
                );
            }
        }
        catch (Exception ex) when (ex is not RunAgentError)
        {
            throw new ConnectionError(
                $"Failed to initialize RunAgent client: {ex.Message}",
                ex
            );
        }
    }

    /// <summary>
    /// Execute agent synchronously (non-streaming)
    /// </summary>
    public async Task<object?> RunAsync(Dictionary<string, object>? kwargs = null)
    {
        ValidateNonStreamEntrypoint();

        return await _restClient.RunAgent(
            _agentId,
            _entrypointTag,
            inputKwargs: kwargs,
            userId: _userId,
            persistentMemory: _persistentMemory
        );
    }

    /// <summary>
    /// Execute agent synchronously with positional and keyword arguments
    /// </summary>
    public async Task<object?> RunAsync(
        List<object>? args = null,
        Dictionary<string, object>? kwargs = null
    )
    {
        ValidateNonStreamEntrypoint();

        return await _restClient.RunAgent(
            _agentId,
            _entrypointTag,
            inputArgs: args,
            inputKwargs: kwargs,
            userId: _userId,
            persistentMemory: _persistentMemory
        );
    }

    /// <summary>
    /// Execute agent with streaming (yields results incrementally)
    /// </summary>
    public IAsyncEnumerable<string> RunStreamAsync(Dictionary<string, object>? kwargs = null)
    {
        ValidateStreamEntrypoint();

        return _socketClient.RunStream(
            _agentId,
            _entrypointTag,
            inputKwargs: kwargs,
            userId: _userId,
            persistentMemory: _persistentMemory
        );
    }

    /// <summary>
    /// Execute agent with streaming and positional/keyword arguments
    /// </summary>
    public IAsyncEnumerable<string> RunStreamAsync(
        List<object>? args = null,
        Dictionary<string, object>? kwargs = null
    )
    {
        ValidateStreamEntrypoint();

        return _socketClient.RunStream(
            _agentId,
            _entrypointTag,
            inputArgs: args,
            inputKwargs: kwargs,
            userId: _userId,
            persistentMemory: _persistentMemory
        );
    }

    /// <summary>
    /// Get agent architecture
    /// </summary>
    public AgentArchitecture? GetAgentArchitecture() => _architecture;

    /// <summary>
    /// Health check for agent availability
    /// </summary>
    public async Task<bool> HealthCheckAsync() => await _restClient.HealthCheck();

    /// <summary>
    /// Get agent ID
    /// </summary>
    public string GetAgentId() => _agentId;

    /// <summary>
    /// Get entrypoint tag
    /// </summary>
    public string GetEntrypointTag() => _entrypointTag;

    /// <summary>
    /// Check if running in local mode
    /// </summary>
    public bool IsLocal() => _isLocal;

    /// <summary>
    /// Get user ID for persistent memory
    /// </summary>
    public string? GetUserId() => _userId;

    /// <summary>
    /// Check if persistent memory is enabled
    /// </summary>
    public bool IsPersistentMemoryEnabled() => _persistentMemory;

    /// <summary>
    /// Get extra parameters
    /// </summary>
    public Dictionary<string, object>? GetExtraParams() => _extraParams;

    /// <summary>
    /// Validate that current entrypoint is NOT a streaming entrypoint
    /// </summary>
    private void ValidateNonStreamEntrypoint()
    {
        if (_entrypointTag.EndsWith("_stream"))
        {
            throw new ValidationError(
                $"STREAM_ENTRYPOINT: Entrypoint '{_entrypointTag}' is a streaming entrypoint. " +
                "Use RunStreamAsync() instead of RunAsync() for streaming entrypoints."
            );
        }
    }

    /// <summary>
    /// Validate that current entrypoint IS a streaming entrypoint
    /// </summary>
    private void ValidateStreamEntrypoint()
    {
        if (!_entrypointTag.EndsWith("_stream"))
        {
            throw new ValidationError(
                $"NON_STREAM_ENTRYPOINT: Entrypoint '{_entrypointTag}' is not a streaming entrypoint. " +
                "Use RunAsync() instead of RunStreamAsync() for non-streaming entrypoints."
            );
        }
    }

    public void Dispose()
    {
        _restClient?.Dispose();
        _socketClient?.Dispose();
    }
}
