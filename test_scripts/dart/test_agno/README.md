# Test Agno - Dart SDK Example

This is a test script for the RunAgent Dart SDK using the Agno agent.

## Setup

1. Make sure you have Dart 3.0+ installed
2. Install dependencies:
   ```bash
   dart pub get
   ```

## Running

### Async Non-Streaming (Active)
```bash
dart run lib/main.dart
```

This will run the async non-streaming example that's currently active in `lib/main.dart`.

### Other Examples

The file contains commented-out examples for:
- Async streaming
- Sync non-streaming (using Future.then)
- Sync streaming (using Future.then)

To use any of these, uncomment the desired example and comment out the active one.

## Configuration

Update the `agentId` and `entrypointTag` in `lib/main.dart` to match your agent configuration.

For local agents, you can also set:
```dart
RunAgentClientConfig.create(
  agentId: 'your-agent-id',
  entrypointTag: 'agno_print_response',
  local: true,
  host: '127.0.0.1',
  port: 8450,
)
```

