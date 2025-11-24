import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:runagent/src/errors/errors.dart';
import 'package:runagent/src/utils/constants.dart';

/// WebSocket client for RunAgent streaming
class SocketClient {
  final String baseSocketUrl;
  final String? apiKey;
  final bool isLocal;

  SocketClient({
    required this.baseSocketUrl,
    this.apiKey,
    this.isLocal = false,
  });

  /// Run agent with streaming
  Stream<dynamic> runStream(
    String agentId,
    String entrypointTag,
    List<dynamic> inputArgs,
    Map<String, dynamic> inputKwargs, {
    int timeoutSeconds = 600,
  }) async* {
    // Build WebSocket URL
    String uri;
    if (isLocal) {
      uri = '$baseSocketUrl${RunAgentConstants.defaultApiPrefix}/agents/$agentId/run-stream';
    } else {
      if (apiKey == null) {
        throw AuthenticationError(
          message: 'api_key is required for remote streaming',
          suggestion: 'Set RUNAGENT_API_KEY or pass Config.APIKey',
        );
      }
      uri = '$baseSocketUrl${RunAgentConstants.defaultApiPrefix}/agents/$agentId/run-stream?token=$apiKey';
    }

    // Ensure proper WebSocket protocol
    String wsUri = uri;
    if (!wsUri.startsWith('ws://') && !wsUri.startsWith('wss://')) {
      if (wsUri.startsWith('http://')) {
        wsUri = wsUri.replaceFirst('http://', 'ws://');
      } else if (wsUri.startsWith('https://')) {
        wsUri = wsUri.replaceFirst('https://', 'wss://');
      } else {
        wsUri = 'wss://$wsUri';
      }
    }
    
    WebSocketChannel? channel;
    try {
      // Create WebSocket connection
      channel = WebSocketChannel.connect(
        Uri.parse(wsUri),
      );

      // Send initial request
      final requestData = {
        'entrypoint_tag': entrypointTag,
        'input_args': inputArgs,
        'input_kwargs': inputKwargs,
        'timeout_seconds': timeoutSeconds,
      };

      channel.sink.add(jsonEncode(requestData));

      // Stream responses
      await for (final message in channel.stream) {
        try {
          final json = jsonDecode(message) as Map<String, dynamic>;
          final type = json['type'] as String?;

          if (type == 'error') {
            final errorData = json['data'] ?? json['error'];
            String errorMessage = 'Stream error';
            String? errorCode;
            String? suggestion;

            if (errorData is Map<String, dynamic>) {
              errorMessage = errorData['message'] ?? errorMessage;
              errorCode = errorData['code'];
              suggestion = errorData['suggestion'];
            } else if (errorData is String) {
              errorMessage = errorData;
            }

            throw RunAgentExecutionError(
              code: errorCode ?? ErrorCodes.serverError,
              message: errorMessage,
              suggestion: suggestion,
            );
          } else if (type == 'status') {
            final status = json['status'] as String?;
            if (status == 'stream_completed') {
              break;
            }
            // Continue for other status messages
          } else if (type == 'data') {
            final data = json['data'] ?? json['content'];
            if (data != null) {
              // Deserialize structured format if present
              yield _deserializeChunk(data);
            }
          } else {
            // Unknown type, yield the whole message
            yield json;
          }
        } catch (e) {
          if (e is RunAgentExecutionError) rethrow;
          // Try to parse as plain string
          if (message is String) {
            yield message;
          } else {
            yield message;
          }
        }
      }
    } catch (e) {
      if (e is RunAgentExecutionError) rethrow;
      throw ConnectionError(
        message: 'Failed to open WebSocket connection: $e',
        suggestion: 'Check your network connection or agent status',
      );
    } finally {
      await channel?.sink.close();
    }
  }

  /// Deserialize chunk data (handles structured format {type, payload})
  dynamic _deserializeChunk(dynamic data) {
    // If data is a string, try to parse as JSON
    if (data is String) {
      try {
        final parsed = jsonDecode(data);
        return _deserializeStructured(parsed);
      } catch (e) {
        return data;
      }
    }
    
    // If data is already a Map, check for structured format
    if (data is Map<String, dynamic>) {
      return _deserializeStructured(data);
    }
    
    return data;
  }

  /// Deserialize structured format {type, payload}
  dynamic _deserializeStructured(dynamic data) {
    if (data is! Map<String, dynamic>) {
      return data;
    }
    
    // Check for structured format {type, payload}
    if (data.containsKey('type') && data.containsKey('payload')) {
      final type = data['type'];
      final payload = data['payload'];
      
      // Parse payload based on type (matching Python serializer logic)
      if (type == 'null') {
        return null;
      } else if (type == 'string') {
        // Payload is a JSON string, parse it to get the actual string
        try {
          return jsonDecode(payload as String);
        } catch (e) {
          return payload;
        }
      } else if (type == 'integer') {
        try {
          final value = jsonDecode(payload as String);
          return value is int ? value : int.parse(value.toString());
        } catch (e) {
          return payload;
        }
      } else if (type == 'number') {
        try {
          final value = jsonDecode(payload as String);
          return value is num ? value : double.parse(value.toString());
        } catch (e) {
          return payload;
        }
      } else if (type == 'boolean') {
        try {
          return jsonDecode(payload as String);
        } catch (e) {
          return payload;
        }
      } else if (type == 'array' || type == 'object') {
        // Parse JSON to get structured data
        try {
          final parsed = jsonDecode(payload as String);
          // If the parsed object also has {content} field, extract it
          if (parsed is Map<String, dynamic> && parsed.containsKey('content')) {
            return parsed['content'];
          }
          return parsed;
        } catch (e) {
          return payload;
        }
      } else {
        // Unknown type, try to parse as JSON
        try {
          return jsonDecode(payload as String);
        } catch (e) {
          return payload;
        }
      }
    }
    
    return data;
  }
}

