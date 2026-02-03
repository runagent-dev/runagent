using RunAgent.Client;
using RunAgent.Types;
using RunAgent.Errors;

namespace RunAgent.Examples;

/// <summary>
/// Example demonstrating persistent memory for stateful agent interactions
/// </summary>
public class PersistentMemoryExample
{
    public static async Task Main(string[] args)
    {
        try
        {
            // Create client with persistent memory enabled
            var config = RunAgentClientConfig
                .Create("YOUR_AGENT_ID", "chat")
                .WithApiKey("your-api-key")
                .WithUserId("user123") // User identifier for memory isolation
                .WithPersistentMemory(true); // Enable persistent memory

            // Initialize client
            var client = await RunAgentClient.CreateAsync(config);

            Console.WriteLine($"User ID: {client.GetUserId()}");
            Console.WriteLine($"Persistent Memory: {client.IsPersistentMemoryEnabled()}");
            Console.WriteLine();

            // First interaction - agent learns user preference
            Console.WriteLine("First interaction:");
            var result1 = await client.RunAsync(new Dictionary<string, object>
            {
                ["message"] = "I prefer dark mode interfaces"
            });
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result1, new System.Text.Json.JsonSerializerOptions
            {
                WriteIndented = true
            }));
            Console.WriteLine();

            // Second interaction - agent remembers the preference
            Console.WriteLine("Second interaction:");
            var result2 = await client.RunAsync(new Dictionary<string, object>
            {
                ["message"] = "What's my UI preference?"
            });
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result2, new System.Text.Json.JsonSerializerOptions
            {
                WriteIndented = true
            }));
            Console.WriteLine();

            Console.WriteLine("Agent successfully remembered context across executions!");

            // Cleanup
            client.Dispose();
        }
        catch (AuthenticationError ex)
        {
            Console.WriteLine($"Authentication Error: {ex.Message}");
        }
        catch (ValidationError ex)
        {
            Console.WriteLine($"Validation Error: {ex.Message}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
        }
    }
}
