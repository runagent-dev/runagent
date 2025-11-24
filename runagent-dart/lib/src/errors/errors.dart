/// RunAgent SDK error types and exceptions

/// Base exception class for all RunAgent errors
class RunAgentError implements Exception {
  final String code;
  final String message;
  final String? suggestion;
  final Map<String, dynamic>? details;

  RunAgentError({
    required this.code,
    required this.message,
    this.suggestion,
    this.details,
  });

  @override
  String toString() => '[$code] $message${suggestion != null ? '\nSuggestion: $suggestion' : ''}';
}

/// Execution error raised when agent execution fails
class RunAgentExecutionError extends RunAgentError {
  RunAgentExecutionError({
    required super.code,
    required super.message,
    super.suggestion,
    super.details,
  });
}

/// Authentication error (401, 403)
class AuthenticationError extends RunAgentError {
  AuthenticationError({
    required super.message,
    super.suggestion,
    super.details,
  }) : super(code: 'AUTHENTICATION_ERROR');
}

/// Permission error (403)
class PermissionError extends RunAgentError {
  PermissionError({
    required super.message,
    super.suggestion,
    super.details,
  }) : super(code: 'PERMISSION_ERROR');
}

/// Connection error (network, DNS, TLS issues)
class ConnectionError extends RunAgentError {
  ConnectionError({
    required super.message,
    super.suggestion,
    super.details,
  }) : super(code: 'CONNECTION_ERROR');
}

/// Validation error (400, 422, bad config)
class ValidationError extends RunAgentError {
  ValidationError({
    required super.message,
    super.suggestion,
    super.details,
  }) : super(code: 'VALIDATION_ERROR');
}

/// Server error (5xx)
class ServerError extends RunAgentError {
  ServerError({
    required super.message,
    super.suggestion,
    super.details,
  }) : super(code: 'SERVER_ERROR');
}

/// Unknown error
class UnknownError extends RunAgentError {
  UnknownError({
    required super.message,
    super.suggestion,
    super.details,
  }) : super(code: 'UNKNOWN_ERROR');
}

/// Error codes matching the checklist taxonomy
class ErrorCodes {
  static const String authenticationError = 'AUTHENTICATION_ERROR';
  static const String permissionError = 'PERMISSION_ERROR';
  static const String connectionError = 'CONNECTION_ERROR';
  static const String validationError = 'VALIDATION_ERROR';
  static const String serverError = 'SERVER_ERROR';
  static const String unknownError = 'UNKNOWN_ERROR';
  static const String agentNotFoundLocal = 'AGENT_NOT_FOUND_LOCAL';
  static const String agentNotFoundRemote = 'AGENT_NOT_FOUND_REMOTE';
  static const String streamEntrypoint = 'STREAM_ENTRYPOINT';
  static const String nonStreamEntrypoint = 'NON_STREAM_ENTRYPOINT';
  static const String architectureMissing = 'ARCHITECTURE_MISSING';
}

