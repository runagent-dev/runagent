import 'dart:io';
import 'package:runagent/runagent.dart';

// Configuration (mirrors test_scripts/python/client_test_lightrag.py)
const String agentId = '63751c14-0ed5-426c-ab44-aa94e5505bed';
const bool localMode = false;
const String userId = 'rad123';

/// Ingest text from a file
Future<dynamic> ingestFromFile(String filePath) async {
  final file = File(filePath);
  if (!await file.exists()) {
    print('Error: File not found: $filePath');
    return null;
  }

  final text = await file.readAsString();
  print('Ingesting ${text.length} characters...');

  final ingestClient = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: agentId,
      entrypointTag: 'ingest_text',
      local: localMode,
      userId: userId,
      persistentMemory: true,
    ),
  );

  final result = await ingestClient.run({'text': text});
  return result;
}

/// Query the RAG system
Future<dynamic> queryRag(String question, {String mode = 'hybrid'}) async {
  print('\nQuerying: $question');

  final queryClient = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: agentId,
      entrypointTag: 'query_rag',
      local: localMode,
      userId: userId,
      persistentMemory: true,
    ),
  );

  final result = await queryClient.run({
    'query': question,
    'mode': mode,
  });

  return result;
}

Future<void> main() async {
  try {
    // Step 1: Ingest text (commented out, same as Python test)
    // print('============================================================');
    // print('STEP 1: Ingest Document');
    // print('============================================================');
    // await ingestFromFile('/home/azureuser/runagent/test/rag_test.txt');

    // Step 2: Query
    print('============================================================');
    print('STEP 2: Query RAG');
    print('============================================================');

    final result = await queryRag('population prediction', mode: 'hybrid');
    print(result);

    // print('\nDone!');
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

