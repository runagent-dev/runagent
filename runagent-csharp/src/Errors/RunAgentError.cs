namespace RunAgent.Errors;

/// <summary>
/// Base exception class for all RunAgent errors
/// </summary>
public class RunAgentError : Exception
{
    public RunAgentError(string message) : base(message) { }
    public RunAgentError(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Authentication error (401, 403) - Missing or invalid API key
/// </summary>
public class AuthenticationError : RunAgentError
{
    public AuthenticationError(string message) : base(message) { }
}

/// <summary>
/// Permission error (403) - Access denied
/// </summary>
public class PermissionError : RunAgentError
{
    public PermissionError(string message) : base(message) { }
}

/// <summary>
/// Connection error - Network issues, DNS, TLS, timeouts
/// </summary>
public class ConnectionError : RunAgentError
{
    public ConnectionError(string message) : base(message) { }
    public ConnectionError(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Validation error (400, 422) - Bad config, missing agent, invalid entrypoint
/// </summary>
public class ValidationError : RunAgentError
{
    public ValidationError(string message) : base(message) { }
}

/// <summary>
/// Server error (5xx) - Backend failures
/// </summary>
public class ServerError : RunAgentError
{
    public ServerError(string message) : base(message) { }
}

/// <summary>
/// Unknown error - Unclassified errors
/// </summary>
public class UnknownError : RunAgentError
{
    public UnknownError(string message) : base(message) { }
    public UnknownError(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Structured execution error with code, message, suggestion, and details
/// </summary>
public class RunAgentExecutionError : RunAgentError
{
    public string Code { get; }
    public string? Suggestion { get; }
    public string? Details { get; }

    public RunAgentExecutionError(
        string code,
        string message,
        string? suggestion = null,
        string? details = null
    ) : base(message)
    {
        Code = code;
        Suggestion = suggestion;
        Details = details;
    }

    public override string ToString()
    {
        var msg = $"[{Code}] {Message}";
        if (!string.IsNullOrEmpty(Suggestion))
            msg += $"\nSuggestion: {Suggestion}";
        if (!string.IsNullOrEmpty(Details))
            msg += $"\nDetails: {Details}";
        return msg;
    }
}
