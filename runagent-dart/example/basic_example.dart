import 'dart:io';
import 'package:runagent/runagent.dart';

/// Basic example of using RunAgent SDK
Future<void> main() async {
  // Create a client for a remote agent
  final client = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: 'YOUR_AGENT_ID',
      entrypointTag: 'generic',
      apiKey: Platform.environment['RUNAGENT_API_KEY'],
    ),
  );

  try {
    // Run the agent with input
    final result = await client.run({
      'message': 'Hello, world!',
      'temperature': 0.7,
    });

    print('Response: $result');
  } catch (e) {
    if (e is RunAgentError) {
      print('Error: ${e.message}');
      if (e.suggestion != null) {
        print('Suggestion: ${e.suggestion}');
      }
    } else {
      print('Unexpected error: $e');
    }
  }
}

