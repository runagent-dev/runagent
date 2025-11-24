/// Type definitions for RunAgent SDK

/// Configuration for RunAgentClient
class RunAgentClientConfig {
  /// Agent ID (required)
  final String agentId;
  
  /// Entrypoint tag (required)
  final String entrypointTag;
  
  /// Whether this is a local agent (default: false)
  final bool? local;
  
  /// Host for local agents (optional, will lookup from DB if not provided and local=true)
  final String? host;
  
  /// Port for local agents (optional, will lookup from DB if not provided and local=true)
  final int? port;
  
  /// API key for remote agents (optional, can also use RUNAGENT_API_KEY env var)
  final String? apiKey;
  
  /// Base URL for remote agents (optional, defaults to https://backend.run-agent.ai)
  final String? baseUrl;
  
  /// Extra parameters for future use
  final Map<String, dynamic>? extraParams;
  
  /// Enable database registry lookup (default: true for local agents)
  final bool? enableRegistry;

  RunAgentClientConfig({
    required this.agentId,
    required this.entrypointTag,
    this.local,
    this.host,
    this.port,
    this.apiKey,
    this.baseUrl,
    this.extraParams,
    this.enableRegistry,
  });

  /// Create a config with required fields
  factory RunAgentClientConfig.create({
    required String agentId,
    required String entrypointTag,
    bool? local,
    String? host,
    int? port,
    String? apiKey,
    String? baseUrl,
    Map<String, dynamic>? extraParams,
    bool? enableRegistry,
  }) {
    return RunAgentClientConfig(
      agentId: agentId,
      entrypointTag: entrypointTag,
      local: local,
      host: host,
      port: port,
      apiKey: apiKey,
      baseUrl: baseUrl,
      extraParams: extraParams,
      enableRegistry: enableRegistry,
    );
  }
}

/// Agent architecture information
class AgentArchitecture {
  final String agentId;
  final List<EntryPoint> entrypoints;

  AgentArchitecture({
    required this.agentId,
    required this.entrypoints,
  });

  factory AgentArchitecture.fromJson(Map<String, dynamic> json) {
    final agentIdValue = json['agent_id'] ?? json['agentId'];
    final entrypointsValue = json['entrypoints'];
    
    return AgentArchitecture(
      agentId: agentIdValue is String ? agentIdValue : (agentIdValue?.toString() ?? ''),
      entrypoints: entrypointsValue is List
          ? (entrypointsValue as List)
              .whereType<Map<String, dynamic>>()
              .map((e) => EntryPoint.fromJson(e))
              .toList()
          : [],
    );
  }
}

/// Entry point definition
class EntryPoint {
  final String tag;
  final String? file;
  final String? module;
  final String? extractor;
  final String? description;

  EntryPoint({
    required this.tag,
    this.file,
    this.module,
    this.extractor,
    this.description,
  });

  factory EntryPoint.fromJson(Map<String, dynamic> json) {
    final tagValue = json['tag'];
    return EntryPoint(
      tag: tagValue is String ? tagValue : (tagValue?.toString() ?? ''),
      file: json['file'] is String ? json['file'] : null,
      module: json['module'] is String ? json['module'] : null,
      extractor: json['extractor'] is String ? json['extractor'] : null,
      description: json['description'] is String ? json['description'] : null,
    );
  }
}

/// Run input payload
class RunInput {
  final List<dynamic> inputArgs;
  final Map<String, dynamic> inputKwargs;
  final int timeoutSeconds;
  final bool asyncExecution;

  RunInput({
    this.inputArgs = const [],
    this.inputKwargs = const {},
    this.timeoutSeconds = 300,
    this.asyncExecution = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'entrypoint_tag': '', // Will be set by client
      'input_args': inputArgs,
      'input_kwargs': inputKwargs,
      'timeout_seconds': timeoutSeconds,
      'async_execution': asyncExecution,
    };
  }
}

