// Async version non-streaming
using RunAgent.Client;
using RunAgent.Types;
using RunAgent.Errors;

class Program
{
    static async Task Main(string[] args)
    {
        try
        {
            var config = RunAgentClientConfig.Create(
                agentId: "ae29bd73-b3d3-99c8-a98f-5d7aec7ee911",
                entrypointTag: "agno_print_response"
            );
            config.WithLocal(true);

            var client = await RunAgentClient.CreateAsync(config);

            var response = await client.RunAsync(new Dictionary<string, object>
            {
                ["prompt"] = "which is better toyota or land rover"
            });

            Console.WriteLine($"Response: {response}");
        }
        catch (RunAgentError ex)
        {
            Console.WriteLine($"Error: {ex.Message}");
            if (ex is RunAgentExecutionError execError && execError.Suggestion != null)
            {
                Console.WriteLine($"Suggestion: {execError.Suggestion}");
            }
            Environment.Exit(1);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Unexpected error: {ex.Message}");
            Environment.Exit(1);
        }
    }
}

// ******************************Streaming Part with agno****************************************
// Async version streaming (C# idiomatic approach)

// using RunAgent.Client;
// using RunAgent.Types;
// using RunAgent.Errors;

// class Program
// {
//     static async Task Main(string[] args)
//     {
//         try
//         {
//             var config = RunAgentClientConfig.Create(
//                 agentId: "ae29bd73-b3d3-99c8-a98f-5d7aec7ee911",
//                 entrypointTag: "agno_print_response_stream"
//             );
//             config.WithLocal(true);
//             var client = await RunAgentClient.CreateAsync(config);

//             // Real streaming - processes chunks as they arrive (idiomatic C#/.NET)
//             // This is the recommended approach for .NET developers
//             await foreach (var chunk in client.RunStreamAsync(new Dictionary<string, object>
//             {
//                 ["prompt"] = "tell me a short story about scotland"
//             }))
//             {
//                 Console.WriteLine($"Response: {chunk}");
//             }

//             // Cleanup
//             client.Dispose();
//         }
//         catch (RunAgentError ex)
//         {
//             Console.WriteLine($"Error: {ex.Message}");
//             if (ex is RunAgentExecutionError execError && execError.Suggestion != null)
//             {
//                 Console.WriteLine($"Suggestion: {execError.Suggestion}");
//             }
//             Environment.Exit(1);
//         }
//         catch (Exception ex)
//         {
//             Console.WriteLine($"Unexpected error: {ex.Message}");
//             Environment.Exit(1);
//         }
//     }
// }
