import 'package:runagent/runagent.dart';

Future<void> main() async {
  try {
    // Create client (update agent_id after deployment)
    final client = await RunAgentClient.create(
      RunAgentClientConfig.create(
        agentId: '9fac4988-d88e-4d6c-994c-7495c14de8b9',
        entrypointTag: 'create_article'
        // local: true, host: '127.0.0.1', port: 8451,
      ),
    );

    print('🗞️ Testing AI Journalist Agent');
    print('=' * 50);

    // Run article creation once (non-streaming)
    final response = await client.run({
      'topic': 'Recent developments in electric bike in south asia',
    });

    print('\nResponse Map:');
    print(response);
    print('\n' + '=' * 50);
    print('✅ Article generation completed!');
  } catch (e) {
    if (e is RunAgentError) {
      print('❌ Error: ${e.message}');
      if (e.suggestion != null) {
        print('Suggestion: ${e.suggestion}');
      }
    } else {
      print('❌ Unexpected error: $e');
    }
  }
}