import 'dart:io';
import 'package:runagent/runagent.dart';

/// Example of using RunAgent SDK with streaming
Future<void> main() async {
  // Create a client for a streaming agent
  final client = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: 'YOUR_AGENT_ID',
      entrypointTag: 'generic_stream', // Note: _stream suffix
      apiKey: Platform.environment['RUNAGENT_API_KEY'],
    ),
  );

  try {
    // Run the agent with streaming
    await for (final chunk in client.runStream({
      'message': 'Tell me a story',
    })) {
      print('Chunk: $chunk');
    }
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

