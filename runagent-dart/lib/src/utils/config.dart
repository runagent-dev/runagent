import 'dart:io';
import 'package:runagent/src/utils/constants.dart';

/// Configuration utilities for loading from environment variables
class ConfigUtils {
  /// Get API key from environment or return null
  static String? getApiKey() {
    return Platform.environment[RunAgentConstants.envApiKey];
  }

  /// Get base URL from environment or return default
  static String getBaseUrl() {
    return Platform.environment[RunAgentConstants.envBaseUrl] ??
        RunAgentConstants.defaultBaseUrl;
  }

  /// Get local flag from environment
  static bool? getLocal() {
    final value = Platform.environment[RunAgentConstants.envLocalAgent];
    if (value == null) return null;
    return value.toLowerCase() == 'true';
  }

  /// Get host from environment
  static String? getHost() {
    return Platform.environment[RunAgentConstants.envAgentHost];
  }

  /// Get port from environment
  static int? getPort() {
    final value = Platform.environment[RunAgentConstants.envAgentPort];
    if (value == null) return null;
    return int.tryParse(value);
  }

  /// Get timeout from environment
  static int? getTimeout() {
    final value = Platform.environment[RunAgentConstants.envTimeout];
    if (value == null) return null;
    return int.tryParse(value);
  }

  /// Resolve boolean with precedence: explicit > env > default
  static bool resolveBool(bool? explicit, bool? env, bool defaultValue) {
    if (explicit != null) return explicit;
    if (env != null) return env;
    return defaultValue;
  }

  /// Get first non-empty string from list
  static String? firstNonEmpty(List<String?> values) {
    for (final value in values) {
      if (value != null && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return null;
  }

  /// Get first non-zero integer from list
  static int? firstNonZero(List<int?> values) {
    for (final value in values) {
      if (value != null && value > 0) {
        return value;
      }
    }
    return null;
  }
}

