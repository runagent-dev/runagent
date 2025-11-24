/// Constants used throughout the RunAgent SDK
class RunAgentConstants {
  /// Default base URL for remote RunAgent service
  static const String defaultBaseUrl = 'https://backend.run-agent.ai';
  
  /// Default API prefix
  static const String defaultApiPrefix = '/api/v1';
  
  /// Default port for local agents
  static const int defaultLocalPort = 8450;
  
  /// Default host for local agents
  static const String defaultLocalHost = '127.0.0.1';
  
  /// Default timeout in seconds
  static const int defaultTimeoutSeconds = 300;
  
  /// Default stream timeout in seconds
  static const int defaultStreamTimeout = 600;
  
  /// Local cache directory path (relative to home)
  static const String localCacheDirectory = '.runagent';
  
  /// Database file name
  static const String databaseFileName = 'runagent_local.db';
  
  /// Environment variable names
  static const String envApiKey = 'RUNAGENT_API_KEY';
  static const String envBaseUrl = 'RUNAGENT_BASE_URL';
  static const String envLocalAgent = 'RUNAGENT_LOCAL';
  static const String envAgentHost = 'RUNAGENT_HOST';
  static const String envAgentPort = 'RUNAGENT_PORT';
  static const String envTimeout = 'RUNAGENT_TIMEOUT';
  
  /// User agent string
  static String userAgent() => 'runagent-dart/0.1.0';
}

