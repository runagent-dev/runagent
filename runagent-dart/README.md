## RunAgent Dart/Flutter SDK

The Dart SDK mirrors the Python CLI client so Dart/Flutter services can trigger hosted or local RunAgent deployments. It wraps the `/api/v1/agents/{agent_id}/run` and `/run-stream` endpoints, handles auth/discovery, and translates responses into Dart-friendly types.

---

### Feature Overview

- **Native Dart arguments**: Pass maps and lists directly
- **Streaming and non-streaming guardrails**:
  - `run()` rejects `*_stream` tags with a helpful error
  - `runStream()` rejects non-stream tags with a helpful error
- **Local vs Remote**:
  - Local DB discovery from `~/.runagent/runagent_local.db` (override with `host`/`port`)
  - Remote uses `RUNAGENT_BASE_URL` (default `https://backend.run-agent.ai`) and Bearer token
- **Authentication**:
  - `Authorization: Bearer RUNAGENT_API_KEY` automatically for remote calls
  - WS token fallback `?token=...` for streams
- **Error taxonomy**:
  - `AUTHENTICATION_ERROR`, `CONNECTION_ERROR`, `VALIDATION_ERROR`, `SERVER_ERROR`, `UNKNOWN_ERROR`
  - Execution errors include `code`, `suggestion`, `details` when provided by backend
- **Architecture**:
  - `getAgentArchitecture()` normalizes envelope and legacy formats and enforces `ARCHITECTURE_MISSING` when needed
- **Config precedence**:
  - Explicit `RunAgentClientConfig` fields → environment → defaults
- **Extra params**:
  - `RunAgentClientConfig.extraParams` stored and retrievable via `client.getExtraParams()`

---

### Installation

#### Option 1: Local Development (Current Setup)

If you're developing locally or the package isn't published to pub.dev yet, use a path dependency:

```yaml
dependencies:
  runagent:
    path: ../runagent-dart  # Adjust path relative to your project
```

Or use an absolute path:

```yaml
dependencies:
  runagent:
    path: /home/azureuser/runagent/runagent-dart
```

#### Option 2: From pub.dev (When Published)

Once the package is published to pub.dev, you can use:

```yaml
dependencies:
  runagent: ^0.1.0
```

Then run:

```bash
flutter pub get
# or
dart pub get
```

**Note:** Requires Dart 3.0+.

---

### Configuration Precedence

1. Explicit `RunAgentClientConfig` fields  
2. Environment variables  
   - `RUNAGENT_API_KEY`  
   - `RUNAGENT_BASE_URL` (defaults to `https://backend.run-agent.ai`)  
   - `RUNAGENT_LOCAL`, `RUNAGENT_HOST`, `RUNAGENT_PORT`, `RUNAGENT_TIMEOUT`  
3. Library defaults (e.g., local DB discovery, 300 s timeout)

When `local` is `true` (or `RUNAGENT_LOCAL=true`), the SDK reads `~/.runagent/runagent_local.db` to discover the host/port unless they're provided directly.

---

### Local vs Remote: Host/Port Optionality

- **Remote** (cloud or self-hosted base URL):
  - Do not set `host`/`port`. Provide `apiKey` (or set `RUNAGENT_API_KEY`), and optionally `baseUrl`.
  - Example:
    ```dart
    final client = await RunAgentClient.create(
      RunAgentClientConfig.create(
        agentId: 'id',
        entrypointTag: 'minimal',
        apiKey: Platform.environment['RUNAGENT_API_KEY'],
        // baseUrl optional; defaults to https://backend.run-agent.ai
      ),
    );
    ```
- **Local**:
  - `host`/`port` are optional. If either is missing, the SDK discovers the value(s) from `~/.runagent/runagent_local.db` for the given `agentId`.
  - If discovery fails (agent not registered), you'll get a clear `VALIDATION_ERROR` suggesting to pass `host`/`port` or register the agent locally.
  - Examples:
    ```dart
    // Rely fully on DB discovery (no host/port)
    final client = await RunAgentClient.create(
      RunAgentClientConfig.create(
        agentId: 'local-id',
        entrypointTag: 'generic',
        local: true,
      ),
    );
    
    // Provide only host, let port be discovered
    final client = await RunAgentClient.create(
      RunAgentClientConfig.create(
        agentId: 'local-id',
        entrypointTag: 'generic',
        local: true,
        host: '127.0.0.1',
      ),
    );
    ```

---

### Quickstart (Remote)

```dart
import 'dart:io';
import 'package:runagent/runagent.dart';

Future<void> main() async {
  final client = await RunAgentClient.create(
    RunAgentClientConfig.create(
      agentId: 'YOUR_AGENT_ID',
      entrypointTag: 'minimal',
      apiKey: Platform.environment['RUNAGENT_API_KEY'],
    ),
  );

  try {
    final result = await client.run({
      'message': 'Summarize Q4 retention metrics',
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
}
```

---

### Quickstart (Local)

```dart
final client = await RunAgentClient.create(
  RunAgentClientConfig.create(
    agentId: 'local-agent-id',
    entrypointTag: 'generic',
    local: true,
    host: '127.0.0.1', // optional: falls back to DB entry
    port: 8450,
  ),
);
```

If `host`/`port` are omitted, the SDK looks up the agent in `~/.runagent/runagent_local.db`. Missing entries yield a helpful `VALIDATION_ERROR`.

---

### Streaming Responses

```dart
await for (final chunk in client.runStream({
  'prompt': 'Stream a haiku about Dart',
})) {
  print(chunk);
}
```

- Local streams connect to `ws://{host}:{port}/api/v1/agents/{id}/run-stream`.  
- Remote streams upgrade to `wss://backend.run-agent.ai/api/v1/...` and append `?token=RUNAGENT_API_KEY`.

---

### Extra Params & Metadata

`RunAgentClientConfig.extraParams` accepts arbitrary metadata; call `client.getExtraParams()` to retrieve a copy. Reserved for future features (tracing, tags) without breaking the API.

---

### Error Handling

All SDK errors extend `RunAgentError` and expose concrete error types:

| Type | Meaning | Typical Fix |
| --- | --- | --- |
| `AUTHENTICATION_ERROR` | API key missing/invalid | Set `RUNAGENT_API_KEY` or `Config.apiKey` |
| `CONNECTION_ERROR` | Network/DNS/TLS issues | Verify network, agent uptime |
| `VALIDATION_ERROR` | Bad config or missing agent | Check `agentId`, entrypoint, local DB |
| `SERVER_ERROR` | Upstream failure (5xx) | Retry or inspect agent logs |

Remote responses that return a structured `error` block become `RunAgentExecutionError` with `code`, `suggestion`, and `details` copied directly.

Use `catch (e)` and check `e is RunAgentError` to inspect fields.

---

### Testing & Troubleshooting

- `dart test` exercises the SDK build.
- Enable debug logging in your application to capture request IDs.
- For local issues, run `runagent cli agents list` to confirm the SQLite database contains the agent and the host/port match.
- For remote failures, confirm the agent is deployed and the entrypoint tag is enabled in the RunAgent Cloud dashboard.

---

### Publishing

See `PUBLISH.md` in this directory for release instructions (version bumps, tagging, and pub.dev publishing).

