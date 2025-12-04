import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:runagent/src/errors/errors.dart';
import 'package:runagent/src/utils/constants.dart';

/// REST client for RunAgent API
class RestClient {
  final String baseUrl;
  final String? apiKey;
  final bool isLocal;

  RestClient({
    required this.baseUrl,
    this.apiKey,
    this.isLocal = false,
  });

  /// Get agent architecture
  Future<Map<String, dynamic>> getAgentArchitecture(String agentId) async {
    final url = Uri.parse('$baseUrl${RunAgentConstants.defaultApiPrefix}/agents/$agentId/architecture');
    
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'User-Agent': RunAgentConstants.userAgent(),
    };

    if (!isLocal && apiKey != null) {
      headers['Authorization'] = 'Bearer $apiKey';
    }

    try {
      final response = await http.get(url, headers: headers);
      
      if (response.statusCode != 200) {
        throw _translateHttpError(response.statusCode, response.body);
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return json;
    } catch (e) {
      if (e is RunAgentError) rethrow;
      throw ConnectionError(
        message: 'Failed to reach RunAgent service: $e',
        suggestion: 'Check your network connection or agent status',
      );
    }
  }

  /// Run agent via REST
  Future<Map<String, dynamic>> runAgent(
    String agentId,
    String entrypointTag,
    List<dynamic> inputArgs,
    Map<String, dynamic> inputKwargs, {
    int timeoutSeconds = 300,
    bool asyncExecution = false,
    String? userId,
    bool persistentMemory = false,
  }) async {
    final url = Uri.parse('$baseUrl${RunAgentConstants.defaultApiPrefix}/agents/$agentId/run');
    
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'User-Agent': RunAgentConstants.userAgent(),
    };

    if (!isLocal && apiKey != null) {
      headers['Authorization'] = 'Bearer $apiKey';
    } else if (!isLocal && apiKey == null) {
      throw AuthenticationError(
        message: 'api_key is required for remote runs',
        suggestion: 'Set RUNAGENT_API_KEY or pass Config.APIKey',
      );
    }

    final payload = <String, dynamic>{
      'entrypoint_tag': entrypointTag,
      'input_args': inputArgs,
      'input_kwargs': inputKwargs,
      'timeout_seconds': timeoutSeconds,
      'async_execution': asyncExecution,
    };

    // Add persistent storage parameters if provided (matches Python SDK)
    if (userId != null) {
      payload['user_id'] = userId;
    }
    if (persistentMemory) {
      payload['persistent_memory'] = persistentMemory;
    }

    try {
      final response = await http.post(
        url,
        headers: headers,
        body: jsonEncode(payload),
      ).timeout(Duration(seconds: timeoutSeconds + 10));

      if (response.statusCode != 200) {
        throw _translateHttpError(response.statusCode, response.body);
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      return json;
    } catch (e) {
      if (e is RunAgentError) rethrow;
      if (e is TimeoutException) {
        throw ConnectionError(
          message: 'Request timed out after ${timeoutSeconds}s',
          suggestion: 'Increase timeout or check agent status',
        );
      }
      throw ConnectionError(
        message: 'Failed to reach RunAgent service: $e',
        suggestion: 'Check your network connection or agent status',
      );
    }
  }

  /// Health check
  Future<bool> healthCheck() async {
    try {
      final url = Uri.parse('$baseUrl${RunAgentConstants.defaultApiPrefix}/health');
      final response = await http.get(url);
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Translate HTTP error to RunAgent error
  RunAgentError _translateHttpError(int statusCode, String body) {
    Map<String, dynamic>? errorPayload;
    
    try {
      final json = jsonDecode(body) as Map<String, dynamic>?;
      if (json != null && json.containsKey('error')) {
        errorPayload = _parseApiError(json['error']);
      }
    } catch (e) {
      // Ignore JSON parse errors
    }

    final error = errorPayload ?? {
      'type': 'SERVER_ERROR',
      'message': 'Server returned status $statusCode',
    };

    final errorMessage = error['message'];
    final errorSuggestion = error['suggestion'];
    final errorDetails = error['details'];
    
    if (statusCode == 401 || statusCode == 403) {
      return AuthenticationError(
        message: errorMessage is String ? errorMessage : 'Authentication failed',
        suggestion: errorSuggestion is String ? (errorSuggestion.isEmpty ? 'Set RUNAGENT_API_KEY or pass Config.APIKey' : errorSuggestion) : 'Set RUNAGENT_API_KEY or pass Config.APIKey',
        details: errorDetails is Map<String, dynamic> ? errorDetails : null,
      );
    } else if (statusCode >= 500) {
      return ServerError(
        message: errorMessage is String ? errorMessage : 'Server error',
        suggestion: errorSuggestion is String ? errorSuggestion : null,
        details: errorDetails is Map<String, dynamic> ? errorDetails : null,
      );
    } else {
      return ValidationError(
        message: errorMessage is String ? errorMessage : 'Validation error',
        suggestion: errorSuggestion is String ? errorSuggestion : null,
        details: errorDetails is Map<String, dynamic> ? errorDetails : null,
      );
    }
  }

  /// Parse API error from response
  Map<String, dynamic>? _parseApiError(dynamic rawError) {
    if (rawError == null) return null;
    
    if (rawError is String) {
      return {
        'type': 'SERVER_ERROR',
        'message': rawError,
      };
    }
    
    if (rawError is Map<String, dynamic>) {
      final message = rawError['message'];
      return {
        'type': rawError['type'] is String ? rawError['type'] : 'SERVER_ERROR',
        'message': message is String ? message : 'Unknown error',
        'code': rawError['code'] is String ? rawError['code'] : null,
        'suggestion': rawError['suggestion'] is String ? rawError['suggestion'] : null,
        'details': rawError['details'] is Map<String, dynamic> ? rawError['details'] : null,
      };
    }
    
    return null;
  }
}

