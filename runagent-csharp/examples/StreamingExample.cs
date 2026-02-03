using RunAgent.Client;
using RunAgent.Types;
using RunAgent.Errors;

namespace RunAgent.Examples;

/// <summary>
/// Example demonstrating streaming agent execution with real-time responses
/// </summary>
public class StreamingExample
{
    public static async Task Main(string[] args)
    {
        try
        {
            // Create client configuration for streaming entrypoint
            var config = RunAgentClientConfig
                .Create("YOUR_AGENT_ID", "solve_problem_stream")
                .WithApiKey("your-api-key"); // Or set RUNAGENT_API_KEY environment variable

            // Initialize client
            var client = await RunAgentClient.CreateAsync(config);

            Console.WriteLine("Streaming results:");
            Console.WriteLine("===================");

            // Execute agent with streaming
            await foreach (var chunk in client.RunStreamAsync(new Dictionary<string, object>
            {
                ["query"] = "Fix my phone",
                ["num_solutions"] = 4
            }))
            {
                Console.Write(chunk);
            }

            Console.WriteLine("\n===================");
            Console.WriteLine("Stream completed");

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
