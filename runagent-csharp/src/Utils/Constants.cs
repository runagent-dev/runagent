namespace RunAgent.Utils;

/// <summary>
/// SDK constants for RunAgent client configuration and defaults
/// </summary>
public static class Constants
{
    /// <summary>
    /// Default base URL for remote RunAgent deployments
    /// </summary>
    public const string DefaultBaseUrl = "http://188.245.179.48:7333";

    /// <summary>
    /// API version prefix
    /// </summary>
    public const string ApiPrefix = "/api/v1";

    /// <summary>
    /// Default local host for agent communication
    /// </summary>
    public const string DefaultLocalHost = "127.0.0.1";

    /// <summary>
    /// Default local port for agent communication
    /// </summary>
    public const int DefaultLocalPort = 8450;

    /// <summary>
    /// Default timeout for non-streaming requests (seconds)
    /// </summary>
    public const int DefaultTimeoutSeconds = 300;

    /// <summary>
    /// Default timeout for streaming requests (seconds)
    /// </summary>
    public const int DefaultStreamTimeoutSeconds = 600;

    /// <summary>
    /// Environment variable name for API key
    /// </summary>
    public const string EnvApiKey = "RUNAGENT_API_KEY";

    /// <summary>
    /// Environment variable name for base URL
    /// </summary>
    public const string EnvBaseUrl = "RUNAGENT_BASE_URL";

    /// <summary>
    /// Local cache directory path
    /// </summary>
    public const string LocalCacheDirectory = "~/.runagent";

    /// <summary>
    /// Database file name for local agent discovery
    /// </summary>
    public const string DatabaseFileName = "runagent_local.db";
}
