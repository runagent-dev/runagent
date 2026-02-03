using RunAgent.Client;
using RunAgent.Types;
using RunAgent.Errors;

namespace RunAgent.Examples;

/// <summary>
/// Example demonstrating local agent deployment usage
/// </summary>
public class LocalExample
{
    public static async Task Main(string[] args)
    {
        try
        {
            // Create client configuration for local agent
            var config = RunAgentClientConfig
                .Create("local-agent-id", "generic")
                .WithLocal(true)
                .WithHostAndPort("127.0.0.1", 8450); // Optional: will auto-discover if not specified

            // Initialize client
            var client = await RunAgentClient.CreateAsync(config);

            Console.WriteLine($"Connected to local agent: {client.GetAgentId()}");
            Console.WriteLine($"Entrypoint: {client.GetEntrypointTag()}");

            // Check agent health
            var isHealthy = await client.HealthCheckAsync();
            Console.WriteLine($"Agent health: {(isHealthy ? "OK" : "FAILED")}");

            // Execute agent
            var result = await client.RunAsync(new Dictionary<string, object>
            {
                ["message"] = "Hello from C# SDK!"
            });

            Console.WriteLine("Result:");
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result, new System.Text.Json.JsonSerializerOptions
            {
                WriteIndented = true
            }));

            // Cleanup
            client.Dispose();
        }
        catch (ValidationError ex)
        {
            Console.WriteLine($"Validation Error: {ex.Message}");
            Console.WriteLine("Make sure the local agent is running with: runagent serve .");
        }
        catch (ConnectionError ex)
        {
            Console.WriteLine($"Connection Error: {ex.Message}");
            Console.WriteLine("Make sure the local agent is running and accessible");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }
}
