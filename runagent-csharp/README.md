# RunAgent C# SDK

C# SDK for RunAgent - Secured, reliable AI agent deployment at scale. Run your stack. Let us run your agents.

[![NuGet Version](https://img.shields.io/nuget/v/RunAgent)](https://www.nuget.org/packages/RunAgent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Multi-Language Support**: Access Python AI agents from C#/.NET applications
- **Local & Remote Deployment**: Support for both local development and cloud deployments
- **Streaming & Non-Streaming**: Execute agents synchronously or with real-time streaming
- **Persistent Memory**: Enable stateful interactions with user-isolated memory
- **Type-Safe**: Full C# type safety with async/await patterns
- **Framework Agnostic**: Works with any Python agent framework (LangGraph, CrewAI, Letta, etc.)

## Installation

### NuGet Package Manager
```bash
dotnet add package RunAgent
```

### Package Manager Console
```powershell
Install-Package RunAgent
```

## Quick Start

### Remote Agent Execution

```csharp
using RunAgent.Client;
using RunAgent.Types;

// Create client configuration
var config = RunAgentClientConfig
    .Create("YOUR_AGENT_ID", "solve_problem")
    .WithApiKey("your-api-key"); // Or set RUNAGENT_API_KEY environment variable

// Initialize client
var client = await RunAgentClient.CreateAsync(config);

// Execute agent
var result = await client.RunAsync(new Dictionary<string, object>
{
    ["query"] = "My laptop is slow",
    ["num_solutions"] = 3,
    ["constraints"] = new List<object>
    {
        new Dictionary<string, object>
        {
            ["type"] = "budget",
            ["value"] = 100
        }
    }
});

Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions
{
    WriteIndented = true
}));

// Cleanup
client.Dispose();
```

### Streaming Execution

```csharp
// Create client for streaming entrypoint
var config = RunAgentClientConfig
    .Create("YOUR_AGENT_ID", "solve_problem_stream")
    .WithApiKey("your-api-key");

var client = await RunAgentClient.CreateAsync(config);

// Stream results in real-time
await foreach (var chunk in client.RunStreamAsync(new Dictionary<string, object>
{
    ["query"] = "Fix my phone",
    ["num_solutions"] = 4
}))
{
    Console.Write(chunk);
}

client.Dispose();
```

### Local Agent Development

```csharp
// Connect to local agent
var config = RunAgentClientConfig
    .Create("local-agent-id", "generic")
    .WithLocal(true)
    .WithHostAndPort("127.0.0.1", 8450); // Optional: auto-discovers if not specified

var client = await RunAgentClient.CreateAsync(config);

// Execute local agent
var result = await client.RunAsync(new Dictionary<string, object>
{
    ["message"] = "Hello from C# SDK!"
});

client.Dispose();
```

### Persistent Memory

Enable stateful interactions with persistent memory:

```csharp
// Create client with persistent memory
var config = RunAgentClientConfig
    .Create("YOUR_AGENT_ID", "chat")
    .WithApiKey("your-api-key")
    .WithUserId("user123")        // User identifier for memory isolation
    .WithPersistentMemory(true);  // Enable persistent memory

var client = await RunAgentClient.CreateAsync(config);

// First interaction - agent learns preference
var result1 = await client.RunAsync(new Dictionary<string, object>
{
    ["message"] = "I prefer dark mode interfaces"
});

// Second interaction - agent remembers the preference
var result2 = await client.RunAsync(new Dictionary<string, object>
{
    ["message"] = "What's my UI preference?"
});
// Agent responds: "You prefer dark mode interfaces"

client.Dispose();
```

## Configuration

### Configuration Precedence

Configuration values are resolved in the following order:

1. **Explicit constructor arguments** (highest priority)
2. **Environment variables**
3. **Library defaults** (lowest priority)

### Configuration Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `AgentId` | `string` | Yes | - | Agent identifier |
| `EntrypointTag` | `string` | Yes | - | Entrypoint tag to invoke |
| `Local` | `bool` | No | `false` | Enable local mode |
| `Host` | `string` | No | `127.0.0.1` | Local agent host |
| `Port` | `int` | No | `8450` | Local agent port |
| `ApiKey` | `string` | No | - | API key for remote auth |
| `BaseUrl` | `string` | No | `https://backend.run-agent.ai` | Remote deployment URL |
| `UserId` | `string` | No | - | User ID for memory isolation |
| `PersistentMemory` | `bool` | No | `false` | Enable persistent memory |
| `ExtraParams` | `Dictionary<string, object>` | No | - | Extra metadata parameters |

### Environment Variables

- `RUNAGENT_API_KEY` - API key for remote authentication
- `RUNAGENT_BASE_URL` - Base URL for remote deployments

### Builder Pattern

Use the fluent builder API for configuration:

```csharp
var config = RunAgentClientConfig
    .Create("agent-id", "entrypoint")
    .WithApiKey("key")
    .WithUserId("user123")
    .WithPersistentMemory(true)
    .WithExtraParams(new Dictionary<string, object>
    {
        ["custom_field"] = "value"
    });
```

## Error Handling

The SDK provides a comprehensive error taxonomy:

| Error Type | Description |
|------------|-------------|
| `AuthenticationError` | Missing or invalid API key (HTTP 401, 403) |
| `PermissionError` | Access denied (HTTP 403) |
| `ConnectionError` | Network issues, timeouts, DNS failures |
| `ValidationError` | Bad config, missing agent, invalid entrypoint (HTTP 400, 404, 422) |
| `ServerError` | Backend failures (HTTP 5xx) |
| `RunAgentExecutionError` | Structured execution errors with code, message, suggestion, details |
| `UnknownError` | Unclassified errors |

### Example Error Handling

```csharp
try
{
    var client = await RunAgentClient.CreateAsync(config);
    var result = await client.RunAsync(kwargs);
}
catch (AuthenticationError ex)
{
    Console.WriteLine($"Auth Error: {ex.Message}");
    Console.WriteLine("Set RUNAGENT_API_KEY or pass apiKey in config");
}
catch (ValidationError ex)
{
    Console.WriteLine($"Validation Error: {ex.Message}");
}
catch (RunAgentExecutionError ex)
{
    Console.WriteLine($"Execution Error [{ex.Code}]: {ex.Message}");
    if (ex.Suggestion != null)
        Console.WriteLine($"Suggestion: {ex.Suggestion}");
}
catch (ConnectionError ex)
{
    Console.WriteLine($"Connection Error: {ex.Message}");
}
```

## API Reference

### RunAgentClient

#### Static Methods

- `CreateAsync(RunAgentClientConfig config)` - Create and initialize client
- `CreateFromEnvironmentAsync(string agentId, string entrypointTag)` - Create client from environment variables

#### Instance Methods

- `RunAsync(Dictionary<string, object>? kwargs)` - Execute agent synchronously
- `RunAsync(List<object>? args, Dictionary<string, object>? kwargs)` - Execute with positional and keyword arguments
- `RunStreamAsync(Dictionary<string, object>? kwargs)` - Execute with streaming
- `RunStreamAsync(List<object>? args, Dictionary<string, object>? kwargs)` - Stream with positional and keyword arguments
- `GetAgentArchitecture()` - Get agent architecture definition
- `HealthCheckAsync()` - Check agent availability
- `GetAgentId()` - Get agent ID
- `GetEntrypointTag()` - Get entrypoint tag
- `IsLocal()` - Check if running in local mode
- `GetUserId()` - Get user ID for persistent memory
- `IsPersistentMemoryEnabled()` - Check if persistent memory is enabled
- `GetExtraParams()` - Get extra parameters
- `Dispose()` - Cleanup resources

## Entrypoint Validation

The SDK enforces correct usage of streaming vs non-streaming entrypoints:

- **Streaming entrypoints** (tags ending with `_stream`): Must use `RunStreamAsync()`
- **Non-streaming entrypoints**: Must use `RunAsync()`

Attempting to use the wrong method will throw a `ValidationError` with a helpful suggestion.

## Local Agent Setup

To use local agents:

1. Start your local agent:
   ```bash
   cd my-agent
   runagent serve .
   ```

2. Connect from C#:
   ```csharp
   var config = RunAgentClientConfig
       .Create("local-agent-id", "entrypoint")
       .WithLocal(true);

   var client = await RunAgentClient.CreateAsync(config);
   ```

## Persistent Memory

Persistent Memory enables stateful agent interactions:

- **User Isolation**: Each `UserId` has isolated memory space
- **Cross-Execution**: State persists across multiple agent invocations
- **Multi-Language**: Works seamlessly with all RunAgent SDKs
- **Serverless**: Built on serverless infrastructure that scales automatically

### Use Cases

- Conversational AI with context retention
- Personalized user experiences
- Multi-step workflows
- Learning systems that improve over time

## Security Best Practices

1. **Never hardcode API keys** - Use environment variables or secure configuration
2. **Validate inputs** - Always validate user inputs before passing to agents
3. **Handle errors gracefully** - Implement proper error handling for production use
4. **Use HTTPS** - Always use secure connections for remote agents
5. **Isolate users** - Use unique `UserId` values for multi-tenant applications

## Examples

See the [examples](./examples) directory for complete working examples:

- `BasicExample.cs` - Non-streaming agent execution
- `StreamingExample.cs` - Real-time streaming responses
- `LocalExample.cs` - Local agent deployment
- `PersistentMemoryExample.cs` - Stateful interactions with persistent memory

## Requirements

- .NET 8.0 or higher
- C# 12.0 or higher

## Dependencies

- `System.Text.Json` 9.0.0

## Troubleshooting

### "Authentication failed" error

**Cause**: Missing or invalid API key

**Solution**: Set `RUNAGENT_API_KEY` environment variable or pass `apiKey` in config:

```csharp
var config = RunAgentClientConfig
    .Create("agent-id", "entrypoint")
    .WithApiKey("your-api-key");
```

### "Entrypoint not found" error

**Cause**: Specified entrypoint tag doesn't exist

**Solution**: Check the error message for available entrypoints, or fetch architecture:

```csharp
var architecture = client.GetAgentArchitecture();
foreach (var ep in architecture.Entrypoints)
{
    Console.WriteLine($"Available: {ep.Tag}");
}
```

### Connection timeout

**Cause**: Network issues or agent not responding

**Solution**:
- For local agents: Ensure agent is running with `runagent serve .`
- For remote agents: Check network connectivity and agent status in dashboard

### "STREAM_ENTRYPOINT" or "NON_STREAM_ENTRYPOINT" error

**Cause**: Using wrong method for entrypoint type

**Solution**:
- For `*_stream` tags: Use `RunStreamAsync()`
- For other tags: Use `RunAsync()`

## Contributing

Contributions are welcome! Please see the main [RunAgent repository](https://github.com/runagent-dev/runagent) for contribution guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://docs.run-agent.ai](https://docs.run-agent.ai)
- **Discord**: [Join our Discord community](https://discord.gg/Q9P9AdHVHz)
- **GitHub Issues**: [Report bugs or request features](https://github.com/runagent-dev/runagent-csharp/issues)

## Related Projects

- [runagent-py](https://github.com/runagent-dev/runagent-py) - Python SDK (CLI + Client)
- [runagent-js](https://github.com/runagent-dev/runagent-js) - JavaScript/TypeScript SDK
- [runagent-rs](https://github.com/runagent-dev/runagent-rs) - Rust SDK
- [runagent-go](https://github.com/runagent-dev/runagent-go) - Go SDK
- [runagent-dart](https://github.com/runagent-dev/runagent-dart) - Dart SDK

---

Made with ❤️ by the RunAgent Team
