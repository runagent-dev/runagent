# RunAgent C# SDK Test - Agno Agent

This test script demonstrates the RunAgent C# SDK with a deployed Agno agent.

## Test Agent

- **Agent ID**: `ae29bd73-b3d3-42c8-a98f-5d7aec7ee919`
- **Entrypoints**:
  - `agno_print_response` - Non-streaming response
  - `agno_print_response_stream` - Streaming response

## Prerequisites

1. .NET 8.0 or higher installed
2. RunAgent API key configured (set `RUNAGENT_API_KEY` environment variable)

## Setup

### Option 1: Using Local SDK Reference

The project is already configured to reference the local RunAgent SDK:

```bash
cd /home/dev/radeen/runagent/test_scripts/csharp/test_agno
dotnet restore
```

### Option 2: Using NuGet Package

Modify `test_agno.csproj` to use the published NuGet package:

```xml
<ItemGroup>
  <PackageReference Include="RunAgent" Version="0.1.47" />
</ItemGroup>
```

## Running the Tests

### Set API Key

```bash
export RUNAGENT_API_KEY=your-api-key-here
```

### Run the Test

```bash
dotnet run
```

## Test Versions

The `Program.cs` file includes both versions (commented and active):

### Non-Streaming Version (Commented)

Tests synchronous execution with `agno_print_response` entrypoint:

```csharp
var config = RunAgentClientConfig.Create(
    agentId: "ae29bd73-b3d3-42c8-a98f-5d7aec7ee919",
    entrypointTag: "agno_print_response"
);

var client = await RunAgentClient.CreateAsync(config);

var response = await client.RunAsync(new Dictionary<string, object>
{
    ["prompt"] = "which is better toyota or land rover"
});

Console.WriteLine($"Response: {response}");
```

### Streaming Version (Active)

Tests real-time streaming with `agno_print_response_stream` entrypoint:

```csharp
var config = RunAgentClientConfig.Create(
    agentId: "ae29bd73-b3d3-42c8-a98f-5d7aec7ee919",
    entrypointTag: "agno_print_response_stream"
);

var client = await RunAgentClient.CreateAsync(config);

await foreach (var chunk in client.RunStreamAsync(new Dictionary<string, object>
{
    ["prompt"] = "tell me a short story about scotland"
}))
{
    Console.WriteLine($"Response: {chunk}");
}
```

## Switching Between Versions

To test the non-streaming version:

1. Comment out the streaming version (lines 42-77)
2. Uncomment the non-streaming version (lines 1-39)
3. Run with `dotnet run`

## Expected Output

### Non-Streaming
```
Response: [JSON response from agent]
```

### Streaming
```
Response: [chunk 1]
Response: [chunk 2]
Response: [chunk 3]
...
```

## Troubleshooting

### "Authentication failed" error

Set the `RUNAGENT_API_KEY` environment variable:
```bash
export RUNAGENT_API_KEY=your-api-key-here
```

### "Entrypoint not found" error

Verify the agent is deployed and the entrypoint tag is correct.

### Build errors

Ensure .NET SDK 6.0 or higher is installed:
```bash
dotnet --version
```

## Related Test Scripts

- `../dart/test_agno/` - Dart version of this test
- `../rust/test_agno/` - Rust version of this test
- `../js/test_agno/` - JavaScript version of this test
- `../python/test_agno/` - Python version of this test
