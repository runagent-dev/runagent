# RunAgent PHP SDK

The PHP SDK for RunAgent enables you to trigger hosted or local RunAgent deployments from PHP applications, including WordPress sites. It wraps the `/api/v1/agents/{agent_id}/run` and `/run-stream` endpoints with proper auth, discovery, and error handling.

---

## Features

- **Native PHP arrays**: Pass associative arrays and indexed arrays directly
- **Streaming and non-streaming guardrails**:
  - `run()` rejects `*_stream` tags with a helpful error
  - `runStream()` rejects non-stream tags with a helpful error
- **Local vs Remote**:
  - Local DB discovery from `~/.runagent/runagent_local.db` (override with `host`/`port`)
  - Remote uses `RUNAGENT_BASE_URL` (default `https://backend.run-agent.ai`) and Bearer token
- **Authentication**:
  - `Authorization: Bearer RUNAGENT_API_KEY` automatically for remote calls
  - WebSocket token fallback `?token=...` for streams
- **Error taxonomy**:
  - `AUTHENTICATION_ERROR`, `CONNECTION_ERROR`, `VALIDATION_ERROR`, `SERVER_ERROR`, `UNKNOWN_ERROR`
  - Execution errors include `code`, `suggestion`, `details` when provided by backend
- **Architecture**:
  - `getAgentArchitecture()` normalizes envelope and legacy formats and enforces `ARCHITECTURE_MISSING` when needed
- **Config precedence**:
  - Explicit `RunAgentClientConfig` fields → environment → defaults
- **Extra params**:
  - `RunAgentClientConfig->extraParams` stored and retrievable via `$client->getExtraParams()`
- **WordPress compatible**: Designed to work seamlessly in WordPress environments

---

## Installation

### Via Composer (Recommended)

```bash
composer require runagent/runagent-php
```

### Manual Installation

1. Download or clone this repository
2. Include the autoloader in your project:

```php
require_once '/path/to/runagent-php/vendor/autoload.php';
```

### WordPress Installation

1. Install via Composer in your WordPress project:

```bash
cd wp-content/plugins/your-plugin
composer require runagent/runagent-php
```

2. Or copy the `runagent-php` directory to your plugin/theme and include the autoloader

---

## Requirements

- PHP 8.0 or higher
- cURL extension
- JSON extension
- mbstring extension

---

## Configuration Precedence

1. Explicit `RunAgentClientConfig` properties  
2. Environment variables  
   - `RUNAGENT_API_KEY`  
   - `RUNAGENT_BASE_URL` (defaults to `https://backend.run-agent.ai`)  
   - `RUNAGENT_LOCAL`, `RUNAGENT_HOST`, `RUNAGENT_PORT`, `RUNAGENT_TIMEOUT`  
3. Library defaults (e.g., local DB discovery, 300s timeout)

When `local` is `true` (or `RUNAGENT_LOCAL=true`), the SDK reads `~/.runagent/runagent_local.db` to discover the host/port unless they're provided directly.

---

## Local vs Remote: Host/Port Optionality

### Remote (cloud or self-hosted base URL)

- Do not set `host`/`port`. Provide `apiKey` (or set `RUNAGENT_API_KEY`), and optionally `baseUrl`.
- Example:
  ```php
  use RunAgent\Client\RunAgentClient;
  use RunAgent\Types\RunAgentClientConfig;

  $config = new RunAgentClientConfig(
      agentId: 'YOUR_AGENT_ID',
      entrypointTag: 'minimal',
      apiKey: getenv('RUNAGENT_API_KEY')
      // baseUrl is optional; defaults to https://backend.run-agent.ai
  );
  
  $client = RunAgentClient::create($config);
  ```

### Local

- `host`/`port` are optional. If either is missing, the SDK discovers the value(s) from `~/.runagent/runagent_local.db` for the given `agentId`.
- If discovery fails (agent not registered), you'll get a clear `VALIDATION_ERROR` suggesting to pass `host`/`port` or register the agent locally.
- Examples:
  ```php
  // Rely fully on DB discovery (no host/port)
  $config = new RunAgentClientConfig(
      agentId: 'local-id',
      entrypointTag: 'generic',
      local: true
  );
  
  // Provide only host, let port be discovered
  $config = new RunAgentClientConfig(
      agentId: 'local-id',
      entrypointTag: 'generic',
      local: true,
      host: '127.0.0.1'
  );
  
  // Provide explicit host and port
  $config = new RunAgentClientConfig(
      agentId: 'local-id',
      entrypointTag: 'generic',
      local: true,
      host: '127.0.0.1',
      port: 8450
  );
  ```

---

## Quick Start (Remote)

```php
<?php

require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

try {
    $config = new RunAgentClientConfig(
        agentId: 'YOUR_AGENT_ID',
        entrypointTag: 'minimal',
        apiKey: getenv('RUNAGENT_API_KEY')
    );
    
    $client = RunAgentClient::create($config);

    $result = $client->run([
        'message' => 'Summarize Q4 retention metrics',
    ]);
    
    echo "Response: " . print_r($result, true) . "\n";
    
} catch (RunAgentError $e) {
    echo "Error [{$e->getErrorCode()}]: {$e->getMessage()}\n";
    if ($e->getSuggestion() !== null) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
}
```

---

## Quick Start (Local)

```php
<?php

require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;

$config = new RunAgentClientConfig(
    agentId: 'local-agent-id',
    entrypointTag: 'generic',
    local: true,
    host: '127.0.0.1',  // optional: falls back to DB entry
    port: 8450
);

$client = RunAgentClient::create($config);

$result = $client->run([
    'prompt' => 'Generate a product description',
]);

echo print_r($result, true);
```

If `host`/`port` are omitted, the SDK looks up the agent in `~/.runagent/runagent_local.db`. Missing entries yield a helpful `VALIDATION_ERROR`.

---

## Streaming Responses

```php
<?php

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;

$config = new RunAgentClientConfig(
    agentId: 'YOUR_AGENT_ID',
    entrypointTag: 'chat_stream',  // Must end with '_stream'
    apiKey: getenv('RUNAGENT_API_KEY')
);

$client = RunAgentClient::create($config);

echo "Streaming response:\n";

foreach ($client->runStream([
    'prompt' => 'Write a haiku about PHP',
]) as $chunk) {
    if (is_string($chunk)) {
        echo $chunk;
    } else {
        print_r($chunk);
    }
    flush();
}

echo "\nStream completed\n";
```

- Local streams connect to `ws://{host}:{port}/api/v1/agents/{id}/run-stream`.  
- Remote streams upgrade to `wss://backend.run-agent.ai/api/v1/...` and append `?token=RUNAGENT_API_KEY`.

---

## WordPress Integration

### Basic Usage in WordPress

```php
<?php

// In your theme or plugin
use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;

function generate_ai_content($prompt) {
    try {
        $config = new RunAgentClientConfig(
            agentId: get_option('runagent_agent_id'),
            entrypointTag: 'generic',
            apiKey: get_option('runagent_api_key')
        );
        
        $client = RunAgentClient::create($config);
        return $client->run(['prompt' => $prompt]);
        
    } catch (Exception $e) {
        return 'Error: ' . $e->getMessage();
    }
}

// Use in templates
$content = generate_ai_content('Generate a blog post intro');
echo wp_kses_post($content);
```

### WordPress Plugin Example

See `examples/wordpress_plugin_example.php` for a complete WordPress plugin implementation that includes:

- Admin settings page for configuration
- Shortcode support: `[runagent prompt="Your prompt"]`
- AJAX endpoint for content generation
- Proper WordPress security and sanitization

---

## Extra Params & Metadata

`RunAgentClientConfig->extraParams` accepts arbitrary metadata; call `$client->getExtraParams()` to retrieve a copy. Reserved for future features (tracing, tags) without breaking the API.

```php
$config = new RunAgentClientConfig(
    agentId: 'my-agent',
    entrypointTag: 'generic',
    extraParams: [
        'session_id' => 'user-123',
        'trace_context' => 'request-abc',
    ]
);

$client = RunAgentClient::create($config);
$params = $client->getExtraParams();
// ['session_id' => 'user-123', 'trace_context' => 'request-abc']
```

---

## Error Handling

All SDK errors extend `RunAgentError` and expose concrete error types:

| Type | Meaning | Typical Fix |
| --- | --- | --- |
| `AUTHENTICATION_ERROR` | API key missing/invalid | Set `RUNAGENT_API_KEY` or pass `apiKey` |
| `CONNECTION_ERROR` | Network/DNS/TLS issues | Verify network, agent uptime |
| `VALIDATION_ERROR` | Bad config or missing agent | Check `agentId`, entrypoint, local DB |
| `SERVER_ERROR` | Upstream failure (5xx) | Retry or inspect agent logs |

Remote responses that return a structured `error` block become `RunAgentExecutionError` with `code`, `suggestion`, and `details` copied directly.

```php
try {
    $result = $client->run(['prompt' => 'test']);
} catch (RunAgentError $e) {
    echo "Error Code: " . $e->getErrorCode() . "\n";
    echo "Message: " . $e->getMessage() . "\n";
    
    if ($e->getSuggestion()) {
        echo "Suggestion: " . $e->getSuggestion() . "\n";
    }
    
    if ($e->getDetails()) {
        echo "Details: " . print_r($e->getDetails(), true) . "\n";
    }
}
```

---

## API Reference

### RunAgentClient

#### `create(RunAgentClientConfig $config): RunAgentClient`

Factory method to create a new client instance.

#### `run(array $inputKwargs = []): mixed`

Run the agent with keyword arguments (associative array).

**Throws**: `ValidationError` if called with a streaming entrypoint.

#### `runWithArgs(array $inputArgs = [], array $inputKwargs = []): mixed`

Run the agent with both positional (indexed array) and keyword arguments.

#### `runStream(array $inputKwargs = []): Generator`

Run the agent and return a Generator that yields streamed chunks.

**Throws**: `ValidationError` if called with a non-streaming entrypoint.

#### `runStreamWithArgs(array $inputArgs = [], array $inputKwargs = []): Generator`

Run the agent with streaming and both positional and keyword arguments.

#### `getAgentArchitecture(): AgentArchitecture`

Get the agent's architecture information including available entrypoints.

#### `healthCheck(): bool`

Check if the agent is available and responding.

#### `getAgentId(): string`

Get the agent ID.

#### `getEntrypointTag(): string`

Get the entrypoint tag.

#### `getExtraParams(): ?array`

Get extra parameters passed during initialization.

#### `isLocal(): bool`

Check if using local deployment.

---

## Testing & Troubleshooting

- Run the examples in the `examples/` directory to test your setup
- For local issues, run `runagent cli agents list` to confirm the SQLite database contains the agent and the host/port match
- For remote failures, confirm the agent is deployed and the entrypoint tag is enabled in the RunAgent Cloud dashboard
- Enable error reporting in PHP to see detailed error messages:
  ```php
  error_reporting(E_ALL);
  ini_set('display_errors', 1);
  ```

---

## Examples

See the `examples/` directory for more examples:

- `basic_example.php` - Basic remote agent usage
- `local_example.php` - Local agent with health check
- `streaming_example.php` - Streaming responses
- `wordpress_plugin_example.php` - Complete WordPress plugin

---

## Publishing

See `PUBLISH.md` for release instructions (version bumps, tagging, and Packagist publishing).

---

## License

MIT License - see LICENSE file for details

---

## Support

- Documentation: https://opencode.ai/docs
- GitHub Issues: https://github.com/runagent/runagent
- Email: support@run-agent.ai

---

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

When contributing, please:
1. Follow PSR-12 coding standards
2. Add tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting

---

## Changelog

### 0.1.0 (Initial Release)

- Complete RunAgentClient implementation
- REST and WebSocket support
- Configuration precedence (explicit > env > defaults)
- Full error taxonomy matching SDK checklist
- WordPress integration support
- Streaming and non-streaming guardrails
- Architecture validation
- Local and remote agent support
