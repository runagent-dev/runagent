using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using RunAgent.Errors;
using RunAgent.Types;
using RunAgent.Utils;

namespace RunAgent.Client;

/// <summary>
/// WebSocket client for streaming RunAgent responses
/// </summary>
public class SocketClient : IDisposable
{
    private readonly string _baseUrl;
    private readonly string? _apiKey;
    private readonly bool _isLocal;
    private ClientWebSocket? _webSocket;

    public SocketClient(string baseUrl, string? apiKey, bool isLocal)
    {
        _baseUrl = baseUrl;
        _apiKey = apiKey;
        _isLocal = isLocal;
    }

    /// <summary>
    /// Stream agent execution results via WebSocket
    /// </summary>
    public async IAsyncEnumerable<string> RunStream(
        string agentId,
        string entrypointTag,
        List<object>? inputArgs = null,
        Dictionary<string, object>? inputKwargs = null,
        int timeoutSeconds = Constants.DefaultStreamTimeoutSeconds,
        string? userId = null,
        bool persistentMemory = false
    )
    {
        // Convert HTTP URL to WebSocket URL
        var wsBaseUrl = _baseUrl
            .Replace("https://", "wss://")
            .Replace("http://", "ws://");

        var uri = _isLocal
            ? $"{wsBaseUrl}{Constants.ApiPrefix}/agents/{agentId}/run-stream"
            : $"{wsBaseUrl}{Constants.ApiPrefix}/agents/{agentId}/run-stream?token={_apiKey}";

        _webSocket = new ClientWebSocket();

        // Connect to WebSocket
        try
        {
            await _webSocket.ConnectAsync(new Uri(uri), CancellationToken.None);
        }
        catch (WebSocketException ex)
        {
            throw new ConnectionError($"WebSocket connection failed: {ex.Message}", ex);
        }

        // Send initial request payload
        var payload = new Dictionary<string, object>
        {
            ["entrypoint_tag"] = entrypointTag,
            ["input_args"] = inputArgs ?? new List<object>(),
            ["input_kwargs"] = inputKwargs ?? new Dictionary<string, object>(),
            ["timeout_seconds"] = timeoutSeconds,
            ["async_execution"] = false
        };

        // Add persistent memory parameters if provided
        if (!string.IsNullOrEmpty(userId))
        {
            payload["user_id"] = userId;
        }
        if (persistentMemory)
        {
            payload["persistent_memory"] = persistentMemory;
        }

        var requestJson = JsonSerializer.Serialize(payload);
        var requestBytes = Encoding.UTF8.GetBytes(requestJson);
        await _webSocket.SendAsync(
            new ArraySegment<byte>(requestBytes),
            WebSocketMessageType.Text,
            true,
            CancellationToken.None
        );

        // Receive and yield messages (no try-catch around yield)
        var buffer = new byte[4096];
        var messageBuilder = new StringBuilder();

        try
        {
            while (_webSocket.State == WebSocketState.Open)
            {
                var result = await _webSocket.ReceiveAsync(
                    new ArraySegment<byte>(buffer),
                    CancellationToken.None
                );

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await _webSocket.CloseAsync(
                        WebSocketCloseStatus.NormalClosure,
                        string.Empty,
                        CancellationToken.None
                    );
                    break;
                }

                var chunk = Encoding.UTF8.GetString(buffer, 0, result.Count);
                messageBuilder.Append(chunk);

                if (result.EndOfMessage)
                {
                    var message = messageBuilder.ToString();
                    messageBuilder.Clear();

                    // Parse WebSocket message
                    var content = ParseWebSocketMessage(message);
                    if (content != null)
                    {
                        yield return content;
                    }

                    // Check if stream completed
                    if (IsStreamCompleted(message))
                    {
                        break;
                    }
                }
            }
        }
        finally
        {
            if (_webSocket?.State == WebSocketState.Open)
            {
                await _webSocket.CloseAsync(
                    WebSocketCloseStatus.NormalClosure,
                    string.Empty,
                    CancellationToken.None
                );
            }
            _webSocket?.Dispose();
            _webSocket = null;
        }
    }

    /// <summary>
    /// Parse WebSocket message and extract content
    /// </summary>
    private string? ParseWebSocketMessage(string message)
    {
        try
        {
            using var doc = JsonDocument.Parse(message);
            var root = doc.RootElement;

            // Check message type
            if (!root.TryGetProperty("type", out var typeElement))
            {
                return message; // Return raw message if no type field
            }

            var type = typeElement.GetString();

            switch (type)
            {
                case "error":
                    // Handle error messages
                    if (root.TryGetProperty("code", out var code) &&
                        root.TryGetProperty("message", out var errorMsg))
                    {
                        var suggestion = root.TryGetProperty("suggestion", out var sugg)
                            ? sugg.GetString()
                            : null;
                        var details = root.TryGetProperty("details", out var det)
                            ? det.GetString()
                            : null;

                        throw new RunAgentExecutionError(
                            code.GetString() ?? "UNKNOWN_ERROR",
                            errorMsg.GetString() ?? "Unknown error occurred",
                            suggestion,
                            details
                        );
                    }
                    throw new RunAgentError(root.TryGetProperty("message", out var msg)
                        ? msg.GetString() ?? "Unknown error"
                        : "Unknown error");

                case "status":
                    // Status messages are informational, don't yield them
                    return null;

                case "data":
                    // Extract and return data content
                    if (root.TryGetProperty("content", out var content))
                    {
                        // Try to deserialize as structured data
                        if (content.ValueKind == JsonValueKind.String)
                        {
                            return content.GetString();
                        }
                        else
                        {
                            return JsonSerializer.Serialize(content);
                        }
                    }
                    return null;

                default:
                    return message;
            }
        }
        catch (JsonException)
        {
            // If parsing fails, return raw message
            return message;
        }
    }

    /// <summary>
    /// Check if stream has completed
    /// </summary>
    private bool IsStreamCompleted(string message)
    {
        try
        {
            using var doc = JsonDocument.Parse(message);
            var root = doc.RootElement;

            if (root.TryGetProperty("type", out var type) &&
                type.GetString() == "status" &&
                root.TryGetProperty("status", out var status))
            {
                return status.GetString() == "stream_completed";
            }
        }
        catch (JsonException)
        {
            // Ignore parse errors
        }

        return false;
    }

    public void Dispose()
    {
        if (_webSocket != null)
        {
            if (_webSocket.State == WebSocketState.Open)
            {
                try
                {
                    _webSocket.CloseAsync(
                        WebSocketCloseStatus.NormalClosure,
                        string.Empty,
                        CancellationToken.None
                    ).Wait(TimeSpan.FromSeconds(5));
                }
                catch
                {
                    // Ignore close errors
                }
            }
            _webSocket.Dispose();
        }
    }
}
