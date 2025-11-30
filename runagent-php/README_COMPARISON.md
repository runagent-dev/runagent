# PHP SDK vs Flutter SDK - API Comparison

This document shows how the PHP SDK mirrors the Flutter SDK API design.

## Side-by-Side Comparison

### Creating a Client

#### Flutter (Dart)
```dart
final client = await RunAgentClient.create(
  RunAgentClientConfig.create(
    agentId: 'YOUR_AGENT_ID',
    entrypointTag: 'generic',
    apiKey: Platform.environment['RUNAGENT_API_KEY'],
  ),
);
```

#### PHP
```php
$config = new RunAgentClientConfig(
    agentId: 'YOUR_AGENT_ID',
    entrypointTag: 'generic',
    apiKey: getenv('RUNAGENT_API_KEY')
);

$client = RunAgentClient::create($config);
```

---

### Running an Agent

#### Flutter (Dart)
```dart
try {
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
  }
}
```

#### PHP
```php
try {
    $result = $client->run([
        'message' => 'Hello, world!',
        'temperature' => 0.7,
    ]);
    
    echo "Response: $result\n";
    
} catch (RunAgentError $e) {
    echo "Error: {$e->getMessage()}\n";
    if ($e->getSuggestion() !== null) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
}
```

---

### Streaming Responses

#### Flutter (Dart)
```dart
await for (final chunk in client.runStream({
  'prompt': 'Tell me a story',
})) {
  print(chunk);
}
```

#### PHP
```php
foreach ($client->runStream(['prompt' => 'Tell me a story']) as $chunk) {
    echo $chunk;
    flush();
}
```

---

### Configuration Options

Both SDKs support the same configuration options:

| Option | Flutter Type | PHP Type | Description |
|--------|--------------|----------|-------------|
| `agentId` | String (required) | string (required) | Agent identifier |
| `entrypointTag` | String (required) | string (required) | Entrypoint to invoke |
| `local` | bool? | ?bool | Run locally (default: false) |
| `host` | String? | ?string | Host for local agents |
| `port` | int? | ?int | Port for local agents |
| `apiKey` | String? | ?string | API key for authentication |
| `baseUrl` | String? | ?string | Custom base URL |
| `extraParams` | Map<String, dynamic>? | ?array | Future-proof metadata |

---

### Error Handling

Both SDKs provide structured error handling:

#### Flutter (Dart)
```dart
catch (e) {
  if (e is RunAgentError) {
    print('Code: ${e.code}');
    print('Message: ${e.message}');
    print('Suggestion: ${e.suggestion}');
    print('Details: ${e.details}');
  }
}
```

#### PHP
```php
catch (RunAgentError $e) {
    echo "Code: {$e->getErrorCode()}\n";
    echo "Message: {$e->getMessage()}\n";
    echo "Suggestion: {$e->getSuggestion()}\n";
    echo "Details: {$e->getDetails()}\n";
}
```

---

### Error Types

Both SDKs have the same error hierarchy:

- `RunAgentError` (base)
  - `AuthenticationError`
  - `ValidationError`
  - `ConnectionError`
  - `ServerError`
  - `RunAgentExecutionError`

---

## Complete Example: Your Agent

### Flutter
```dart
import 'dart:io';
import 'package:runagent/runagent.dart';

Future<void> main() async {
  final client = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: '91e70681-def8-4600-8a30-d037c1b51870',
      entrypointTag: 'agno_print_response',
      local: true,
      host: '0.0.0.0',
      port: 8333,
      apiKey: Platform.environment['RUNAGENT_API_KEY'],
    ),
  );

  try {
    final result = await client.run({'prompt': 'Hello!'});
    print('Response: $result');
  } catch (e) {
    if (e is RunAgentError) {
      print('Error: ${e.message}');
    }
  }
}
```

### PHP
```php
<?php
require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

$config = new RunAgentClientConfig(
    agentId: '91e70681-def8-4600-8a30-d037c1b51870',
    entrypointTag: 'agno_print_response',
    local: true,
    host: '0.0.0.0',
    port: 8333,
    apiKey: getenv('RUNAGENT_API_KEY')
);

try {
    $client = RunAgentClient::create($config);
    $result = $client->run(['prompt' => 'Hello!']);
    echo "Response: $result\n";
} catch (RunAgentError $e) {
    echo "Error: {$e->getMessage()}\n";
}
```

---

## Key Differences (Language-Specific)

| Aspect | Flutter | PHP |
|--------|---------|-----|
| **Async/Await** | `await client.run()` | `$client->run()` (synchronous) |
| **Streaming** | `await for (chunk in stream)` | `foreach ($stream as $chunk)` |
| **Config Creation** | `RunAgentClientConfig.create()` | `new RunAgentClientConfig()` |
| **Type Safety** | Strong typing | Gradual typing (PHP 8.0+) |
| **Getters** | `e.message` | `$e->getMessage()` |
| **Null Safety** | `String?` | `?string` |

---

## Summary

The PHP SDK follows the same design patterns as the Flutter SDK:

✅ Same configuration options  
✅ Same method names (`run`, `runStream`)  
✅ Same error types and structure  
✅ Same support for local and remote agents  
✅ Same authentication mechanism  

The APIs are as similar as the languages allow, making it easy to switch between SDKs or reference documentation across languages.
