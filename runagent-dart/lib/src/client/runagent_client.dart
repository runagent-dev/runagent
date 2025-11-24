import 'dart:async';
import 'dart:convert';
import 'package:runagent/src/client/rest_client.dart';
import 'package:runagent/src/client/socket_client.dart';
import 'package:runagent/src/errors/errors.dart';
import 'package:runagent/src/types/types.dart';
import 'package:runagent/src/utils/config.dart';
import 'package:runagent/src/utils/constants.dart';

/// Main client for interacting with RunAgent deployments
class RunAgentClient {
  final String agentId;
  final String entrypointTag;
  final bool local;
  final RestClient restClient;
  final SocketClient socketClient;
  final Map<String, dynamic>? extraParams;
  
  AgentArchitecture? _architecture;

  RunAgentClient._({
    required this.agentId,
    required this.entrypointTag,
    required this.local,
    required this.restClient,
    required this.socketClient,
    this.extraParams,
  });

  /// Create a new RunAgent client from configuration
  static Future<RunAgentClient> create(RunAgentClientConfig config) async {
    // Validate required fields
    if (config.agentId.trim().isEmpty) {
      throw ValidationError(message: 'agent_id is required');
    }
    if (config.entrypointTag.trim().isEmpty) {
      throw ValidationError(message: 'entrypoint_tag is required');
    }

    // Resolve configuration with precedence: explicit > env > default
    final local = ConfigUtils.resolveBool(
      config.local,
      ConfigUtils.getLocal(),
      false,
    );

    final enableRegistry = config.enableRegistry ?? local;

    // Resolve host/port for local agents
    String? host;
    int? port;

    if (local) {
      host = ConfigUtils.firstNonEmpty([
        config.host,
        ConfigUtils.getHost(),
      ]);
      port = ConfigUtils.firstNonZero([
        config.port,
        ConfigUtils.getPort(),
      ]);

      // Try database lookup if enabled and host/port not provided
      if (enableRegistry && (host == null || port == null)) {
        try {
          // TODO: Implement database lookup when sqflite is available
          // For now, we'll require explicit host/port or use defaults
          if (host == null) host = RunAgentConstants.defaultLocalHost;
          if (port == null) port = RunAgentConstants.defaultLocalPort;
        } catch (e) {
          // Database lookup failed, use defaults or throw
          if (host == null || port == null) {
            throw ValidationError(
              message: 'Unable to resolve local host/port',
              suggestion: 'Pass Config.Host/Config.Port or ensure the agent is registered locally',
            );
          }
        }
      }

      if (host == null || port == null) {
        throw ValidationError(
          message: 'Host and port are required for local agents',
          suggestion: 'Pass Config.Host/Config.Port or enable registry for database lookup',
        );
      }
    }

    // Resolve API key (config > env var)
    final apiKey = ConfigUtils.firstNonEmpty([
      config.apiKey,
      ConfigUtils.getApiKey(),
    ]);

    // Resolve base URL (config > env var > default)
    final baseUrl = ConfigUtils.firstNonEmpty([
      config.baseUrl,
      ConfigUtils.getBaseUrl(),
    ]) ?? RunAgentConstants.defaultBaseUrl;

    // Create REST and WebSocket clients
    final (restClient, socketClient) = local
        ? _createLocalClients(host!, port!, apiKey)
        : _createRemoteClients(baseUrl, apiKey);

    final client = RunAgentClient._(
      agentId: config.agentId,
      entrypointTag: config.entrypointTag,
      local: local,
      restClient: restClient,
      socketClient: socketClient,
      extraParams: config.extraParams,
    );

    // Initialize architecture and validate entrypoint
    await client._initializeArchitecture();

    return client;
  }

  /// Create local clients
  static (RestClient, SocketClient) _createLocalClients(
    String host,
    int port,
    String? apiKey,
  ) {
    final restBase = 'http://$host:$port';
    final socketBase = 'ws://$host:$port';

    final restClient = RestClient(
      baseUrl: restBase,
      apiKey: apiKey,
      isLocal: true,
    );

    final socketClient = SocketClient(
      baseSocketUrl: socketBase,
      apiKey: apiKey,
      isLocal: true,
    );

    return (restClient, socketClient);
  }

  /// Create remote clients
  static (RestClient, SocketClient) _createRemoteClients(
    String baseUrl,
    String? apiKey,
  ) {
    // Normalize base URL
    String normalizedBase = baseUrl.trim();
    if (!normalizedBase.startsWith('http://') && !normalizedBase.startsWith('https://')) {
      normalizedBase = 'https://$normalizedBase';
    }
    normalizedBase = normalizedBase.replaceAll(RegExp(r'/$'), '');

    // Convert to WebSocket URL
    String socketBase;
    if (normalizedBase.startsWith('https://')) {
      socketBase = normalizedBase.replaceFirst('https://', 'wss://');
    } else if (normalizedBase.startsWith('http://')) {
      socketBase = normalizedBase.replaceFirst('http://', 'ws://');
    } else {
      socketBase = 'wss://$normalizedBase';
    }

    final restClient = RestClient(
      baseUrl: normalizedBase,
      apiKey: apiKey,
      isLocal: false,
    );

    final socketClient = SocketClient(
      baseSocketUrl: socketBase,
      apiKey: apiKey,
      isLocal: false,
    );

    return (restClient, socketClient);
  }

  /// Initialize architecture and validate entrypoint
  Future<void> _initializeArchitecture() async {
    final architectureJson = await restClient.getAgentArchitecture(agentId);
    
    // Handle envelope format
    if (architectureJson.containsKey('success')) {
      final success = architectureJson['success'] as bool?;
      if (success == false) {
        final error = architectureJson['error'];
        if (error is Map<String, dynamic>) {
          final errorMessage = error['message'];
          final errorCode = error['code'];
          throw RunAgentExecutionError(
            code: errorCode is String ? errorCode : ErrorCodes.serverError,
            message: errorMessage is String ? errorMessage : 'Failed to retrieve agent architecture',
            suggestion: error['suggestion'] is String ? error['suggestion'] : null,
            details: error['details'] is Map<String, dynamic> ? error['details'] : null,
          );
        }
        final message = architectureJson['message'];
        throw ServerError(
          message: message is String ? message : 'Failed to retrieve agent architecture',
        );
      }
      
      final data = architectureJson['data'] as Map<String, dynamic>?;
      if (data != null) {
        _architecture = AgentArchitecture.fromJson(data);
      }
    } else {
      // Legacy format
      _architecture = AgentArchitecture.fromJson(architectureJson);
    }

    // Validate entrypoint exists
    if (_architecture == null || _architecture!.entrypoints.isEmpty) {
      throw ValidationError(
        message: 'Architecture missing entrypoints',
        suggestion: 'Redeploy the agent with entrypoints configured',
      );
    }

    final found = _architecture!.entrypoints.any(
      (ep) => ep.tag == entrypointTag,
    );

    if (!found) {
      final available = _architecture!.entrypoints.map((ep) => ep.tag).join(', ');
      throw ValidationError(
        message: 'Entrypoint `$entrypointTag` not found in agent $agentId',
        suggestion: 'Available entrypoints: $available',
      );
    }

    // Validate stream vs non-stream guardrails
    final isStreamTag = entrypointTag.toLowerCase().endsWith('_stream');
    if (isStreamTag) {
      // This is a stream tag - should use runStream
    } else {
      // This is a non-stream tag - should use run
    }
  }

  /// Run the agent with keyword arguments
  Future<dynamic> run([Map<String, dynamic>? inputKwargs]) async {
    return runWithArgs([], inputKwargs ?? {});
  }

  /// Run the agent with both positional and keyword arguments
  Future<dynamic> runWithArgs(
    List<dynamic> inputArgs,
    Map<String, dynamic> inputKwargs,
  ) async {
    // Guardrail: non-stream only
    if (entrypointTag.toLowerCase().endsWith('_stream')) {
      throw ValidationError(
        message: 'Stream entrypoint must be invoked with runStream',
        suggestion: 'Use client.runStream(...) for *_stream tags',
      );
    }

    final response = await restClient.runAgent(
      agentId,
      entrypointTag,
      inputArgs,
      inputKwargs,
    );

    if (response['success'] == true) {
      // Process response data
      dynamic payload;

      final data = response['data'];
      if (data is String) {
        // Case 1: data is a string (could be structured JSON string with {type, payload})
        payload = _deserializeString(data);
      } else if (data is Map<String, dynamic>) {
        // Case 2: data has result_data.data (legacy detailed execution payload)
        if (data.containsKey('result_data')) {
          final resultData = data['result_data'] as Map<String, dynamic>?;
          final innerData = resultData?['data'];
          // Check if innerData is a string that needs deserialization
          if (innerData is String) {
            payload = _deserializeString(innerData);
          } else {
            payload = _deserializeObject(innerData);
          }
        } else {
          // Case 3: data is an object (could be {type, payload} structure)
          payload = _deserializeObject(data);
        }
      } else if (data != null) {
        payload = _deserializeObject(data);
      } else if (response.containsKey('output_data')) {
        // Case 4: Fallback to output_data (backward compatibility)
        final outputData = response['output_data'];
        if (outputData is String) {
          payload = _deserializeString(outputData);
        } else {
          payload = _deserializeObject(outputData);
        }
      }

      if (payload == null) {
        return null;
      }

      // Check for generator object warning
      if (payload is String) {
        final lowerStr = payload.toLowerCase();
        if (lowerStr.contains('generator object') || lowerStr.contains('<generator')) {
          final streamingTag = '${entrypointTag}_stream';
          throw ValidationError(
            message: 'Agent returned a generator object instead of content. This entrypoint appears to be a streaming function.',
            suggestion: 'Try using the streaming endpoint: `$streamingTag`\nOr use `runStream()` method instead of `run()`.',
          );
        }
      }

      return payload;
    } else {
      // Handle error format
      final error = response['error'];
      if (error is Map<String, dynamic>) {
        final errorMessage = error['message'];
        final errorSuggestion = error['suggestion'];
        final errorDetails = error['details'];
        throw RunAgentExecutionError(
          code: error['code'] is String ? error['code'] : ErrorCodes.serverError,
          message: errorMessage is String ? errorMessage : 'Unknown error',
          suggestion: errorSuggestion is String ? errorSuggestion : null,
          details: errorDetails is Map<String, dynamic> ? errorDetails : null,
        );
      } else if (error is String) {
        throw RunAgentExecutionError(
          code: ErrorCodes.serverError,
          message: error,
        );
      } else {
        throw RunAgentExecutionError(
          code: ErrorCodes.serverError,
          message: 'Unknown error',
        );
      }
    }
  }

  /// Run the agent and return a stream of responses
  Stream<dynamic> runStream([Map<String, dynamic>? inputKwargs]) {
    return runStreamWithArgs([], inputKwargs ?? {});
  }

  /// Run the agent with streaming and both positional and keyword arguments
  Stream<dynamic> runStreamWithArgs(
    List<dynamic> inputArgs,
    Map<String, dynamic> inputKwargs,
  ) {
    // Guardrail: stream only
    if (!entrypointTag.toLowerCase().endsWith('_stream')) {
      throw ValidationError(
        message: 'Non-stream entrypoint must be invoked with run',
        suggestion: 'Use client.run(...) for non-stream tags',
      );
    }

    return socketClient.runStream(
      agentId,
      entrypointTag,
      inputArgs,
      inputKwargs,
    );
  }

  /// Get the agent's architecture information
  Future<AgentArchitecture> getAgentArchitecture() async {
    if (_architecture != null) {
      return _architecture!;
    }

    final architectureJson = await restClient.getAgentArchitecture(agentId);
    
    // Handle envelope format
    if (architectureJson.containsKey('success')) {
      final success = architectureJson['success'] as bool?;
      if (success == false) {
        final error = architectureJson['error'];
        if (error is Map<String, dynamic>) {
          final errorMessage = error['message'];
          final errorCode = error['code'];
          throw RunAgentExecutionError(
            code: errorCode is String ? errorCode : ErrorCodes.serverError,
            message: errorMessage is String ? errorMessage : 'Failed to retrieve agent architecture',
            suggestion: error['suggestion'] is String ? error['suggestion'] : null,
            details: error['details'] is Map<String, dynamic> ? error['details'] : null,
          );
        }
        final message = architectureJson['message'];
        throw ServerError(
          message: message is String ? message : 'Failed to retrieve agent architecture',
        );
      }
      
      final data = architectureJson['data'] as Map<String, dynamic>?;
      if (data != null) {
        _architecture = AgentArchitecture.fromJson(data);
      }
    } else {
      // Legacy format
      _architecture = AgentArchitecture.fromJson(architectureJson);
    }

    if (_architecture == null || _architecture!.entrypoints.isEmpty) {
      throw ValidationError(
        message: 'Architecture missing entrypoints',
        suggestion: 'Redeploy the agent with entrypoints configured',
      );
    }

    return _architecture!;
  }

  /// Check if the agent is available
  Future<bool> healthCheck() async {
    try {
      return await restClient.healthCheck();
    } catch (e) {
      return false;
    }
  }

  /// Get agent ID
  String getAgentId() => agentId;

  /// Get entrypoint tag
  String getEntrypointTag() => entrypointTag;

  /// Get any extra params supplied during initialization
  Map<String, dynamic>? getExtraParams() => extraParams;

  /// Check if using local deployment
  bool isLocal() => local;

  /// Deserialize string payload
  dynamic _deserializeString(String data) {
    try {
      // Try to parse as JSON
      final parsed = jsonDecode(data);
      
      // If it's a structured format {type, payload}, deserialize it
      if (parsed is Map<String, dynamic>) {
        return _deserializeObject(parsed);
      }
      
      return parsed;
    } catch (e) {
      // Return as plain string if JSON parsing fails
      return data;
    }
  }

  /// Deserialize object payload
  dynamic _deserializeObject(dynamic data) {
    // Handle null
    if (data == null) return null;
    
    // If it's not a Map, return as-is
    if (data is! Map<String, dynamic>) {
      return data;
    }
    
    // Check for structured object with payload field (matching Python SDK)
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
          return jsonDecode(payload as String);
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

