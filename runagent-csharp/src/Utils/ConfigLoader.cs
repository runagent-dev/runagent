using RunAgent.Types;

namespace RunAgent.Utils;

/// <summary>
/// Utility for loading and resolving RunAgent configuration
/// Configuration precedence: Constructor args > Environment variables > Defaults
/// </summary>
public static class ConfigLoader
{
    /// <summary>
    /// Resolve API key from config or environment
    /// </summary>
    public static string? ResolveApiKey(string? configApiKey)
    {
        return configApiKey ?? Environment.GetEnvironmentVariable(Constants.EnvApiKey);
    }

    /// <summary>
    /// Resolve base URL from config or environment
    /// </summary>
    public static string ResolveBaseUrl(string? configBaseUrl)
    {
        return configBaseUrl
            ?? Environment.GetEnvironmentVariable(Constants.EnvBaseUrl)
            ?? Constants.DefaultBaseUrl;
    }

    /// <summary>
    /// Resolve host for local agent
    /// </summary>
    public static string ResolveHost(string? configHost)
    {
        return configHost ?? Constants.DefaultLocalHost;
    }

    /// <summary>
    /// Resolve port for local agent
    /// </summary>
    public static int ResolvePort(int? configPort)
    {
        return configPort ?? Constants.DefaultLocalPort;
    }

    /// <summary>
    /// Create a RunAgentClientConfig from environment variables
    /// </summary>
    public static RunAgentClientConfig FromEnvironment(string agentId, string entrypointTag)
    {
        var config = new RunAgentClientConfig(agentId, entrypointTag)
        {
            ApiKey = Environment.GetEnvironmentVariable(Constants.EnvApiKey),
            BaseUrl = Environment.GetEnvironmentVariable(Constants.EnvBaseUrl)
        };
        return config;
    }

    /// <summary>
    /// Expand tilde in path (Unix-style home directory)
    /// </summary>
    public static string ExpandPath(string path)
    {
        if (string.IsNullOrEmpty(path))
            return path;

        if (path.StartsWith("~/") || path == "~")
        {
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return path.Replace("~", home);
        }

        return path;
    }

    /// <summary>
    /// Get local database path
    /// </summary>
    public static string GetLocalDatabasePath()
    {
        var cacheDir = ExpandPath(Constants.LocalCacheDirectory);
        return Path.Combine(cacheDir, Constants.DatabaseFileName);
    }
}
