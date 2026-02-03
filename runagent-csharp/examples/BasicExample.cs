using RunAgent.Client;
using RunAgent.Types;
using RunAgent.Errors;

namespace RunAgent.Examples;

/// <summary>
/// Basic example demonstrating non-streaming agent execution
/// </summary>
public class BasicExample
{
    public static async Task Main(string[] args)
    {
        try
        {
            // Create client configuration
            var config = RunAgentClientConfig
                .Create("YOUR_AGENT_ID", "solve_problem")
                .WithApiKey("your-api-key"); // Or set RUNAGENT_API_KEY environment variable

            // Initialize client
            var client = await RunAgentClient.CreateAsync(config);

            // Execute agent with keyword arguments
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

            Console.WriteLine("Result:");
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result, new System.Text.Json.JsonSerializerOptions
            {
                WriteIndented = true
            }));

            // Cleanup
            client.Dispose();
        }
        catch (AuthenticationError ex)
        {
            Console.WriteLine($"Authentication Error: {ex.Message}");
            Console.WriteLine("Please set RUNAGENT_API_KEY environment variable or pass API key in config");
        }
        catch (ValidationError ex)
        {
            Console.WriteLine($"Validation Error: {ex.Message}");
        }
        catch (ConnectionError ex)
        {
            Console.WriteLine($"Connection Error: {ex.Message}");
        }
        catch (RunAgentExecutionError ex)
        {
            Console.WriteLine($"Execution Error: {ex}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Unexpected Error: {ex.Message}");
        }
    }
}
