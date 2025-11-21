import 'package:runagent/runagent.dart';

/// Example of using RunAgent SDK with a local agent
Future<void> main() async {
  // Create a client for a local agent
  final client = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: 'local-agent-id',
      entrypointTag: 'generic',
      local: true,
      host: '127.0.0.1',
      port: 8450,
    ),
  );

  try {
    // Run the agent with input
    final result = await client.run({
      'message': 'Hello from local agent!',
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

