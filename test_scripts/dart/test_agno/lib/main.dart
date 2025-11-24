// // async version non-streaming
// import 'dart:io';
// import 'package:runagent/runagent.dart';

// Future<void> main() async {
//   try {
//     // Direct config construction
//     final client = await RunAgentClient.create(
//       RunAgentClientConfig.create(
//         agentId: 'ae29bd73-b3d3-42c8-a98f-5d7aec7ee919',
//         entrypointTag: 'agno_print_response',
//       ),
//     );
    
//     final response = await client.run({
//       'prompt': 'which is better toyota or land rover',
//     });
    
//     // Response is a Map, not a String
//     print('Response: $response');  // <-- Added semicolon here
//   } catch (e) {
//     if (e is RunAgentError) {
//       print('Error: ${e.message}');
//       if (e.suggestion != null) {
//         print('Suggestion: ${e.suggestion}');
//       }
//     } else {
//       print('Unexpected error: $e');
//     }
//   }
// }

// ******************************Streaming Part with agno****************************************
// async version streaming (Flutter/Dart idiomatic approach)

import 'dart:io';
import 'package:runagent/runagent.dart';

Future<void> main() async {
  try {
    final client = await RunAgentClient.create(
      RunAgentClientConfig.create(
        agentId: 'ae29bd73-b3d3-42c8-a98f-5d7aec7ee919',
        entrypointTag: 'agno_print_response_stream',
      ),
    );

    // Real streaming - processes chunks as they arrive (idiomatic Dart/Flutter)
    // This is the recommended approach for Flutter developers
    await for (final chunk in client.runStream({
      'prompt': 'tell me a short story about scotland',
    })) {
      print('Response: $chunk');
    }
  } catch (e) {
    if (e is RunAgentError) {
      print('Error: ${e.message}');
      if (e.suggestion != null) {
        print('Suggestion: ${e.suggestion}');
      }
      exit(1);
    } else {
      print('Unexpected error: $e');
      exit(1);
    }
  }
}


