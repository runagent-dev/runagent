# Testing PHP SDK with Your Agent from /nice/ Folder

This guide shows how to use the PHP SDK with your deployed agent.

## Your Agent Details

- **Agent ID**: `91e70681-def8-4600-8a30-d037c1b51870`
- **Location**: `/home/nihal/Desktop/github_repos/runagent/nice/`
- **Endpoint**: `http://0.0.0.0:8333`
- **Framework**: Agno with OpenAI GPT-4o-mini
- **Entrypoints**:
  - `agno_print_response` (non-streaming)
  - `agno_print_response_stream` (streaming)

## Quick Start

### 1. Set OpenAI API Key (Required!)

Your agent uses OpenAI's GPT-4o-mini model, so you need an API key:

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

### 2. Restart the Agent

After setting the API key, restart your agent:

```bash
cd /home/nihal/Desktop/github_repos/runagent/nice
runagent stop
runagent start
```

### 3. Install PHP SDK Dependencies

```bash
cd /home/nihal/Desktop/github_repos/runagent/runagent-php
composer install
```

### 4. Run the Examples

#### Option A: Comprehensive Test Suite

```bash
php examples/nice_agent_test.php
```

This will:
- ✅ Test architecture retrieval
- ✅ Test health check
- ✅ Test agent execution (if OpenAI key is set)
- ✅ Test guardrails (run vs runStream)

#### Option B: Basic Example

```bash
php examples/basic_example_updated.php
```

Simple non-streaming execution.

#### Option C: Streaming Example

```bash
php examples/streaming_example_updated.php
```

Demonstrates streaming responses.

## Example Code (Based on Flutter SDK)

### Non-Streaming Example

```php
<?php
require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

// Create client
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
    
    // Run the agent
    $result = $client->run([
        'prompt' => 'Hello, world! Tell me a fun fact.',
    ]);
    
    echo "Response: $result\n";
    
} catch (RunAgentError $e) {
    echo "Error: {$e->getMessage()}\n";
    if ($e->getSuggestion()) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
}
```

### Streaming Example

```php
<?php
require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

// Create streaming client
$config = new RunAgentClientConfig(
    agentId: '91e70681-def8-4600-8a30-d037c1b51870',
    entrypointTag: 'agno_print_response_stream',
    local: true,
    host: '0.0.0.0',
    port: 8333,
    apiKey: getenv('RUNAGENT_API_KEY')
);

try {
    $client = RunAgentClient::create($config);
    
    // Stream the response
    foreach ($client->runStream(['prompt' => 'Write a haiku']) as $chunk) {
        if (is_array($chunk) && isset($chunk['content'])) {
            echo $chunk['content'];
        } else {
            echo $chunk;
        }
        flush();
    }
    
} catch (RunAgentError $e) {
    echo "Error: {$e->getMessage()}\n";
}
```

## Comparison with Flutter SDK

| Feature | Flutter SDK | PHP SDK |
|---------|-------------|---------|
| **Client Creation** | `await RunAgentClient.create(config)` | `RunAgentClient::create($config)` |
| **Config** | `RunAgentClientConfig.create(...)` | `new RunAgentClientConfig(...)` |
| **Run** | `await client.run({...})` | `$client->run([...])` |
| **Stream** | `await for (chunk in client.runStream({...}))` | `foreach ($client->runStream([...]) as $chunk)` |
| **Error Handling** | `catch (e is RunAgentError)` | `catch (RunAgentError $e)` |
| **Error Message** | `e.message` | `$e->getMessage()` |
| **Suggestion** | `e.suggestion` | `$e->getSuggestion()` |

## Expected Output

When you run `php examples/nice_agent_test.php` with OpenAI key set:

```
╔════════════════════════════════════════════════════════════╗
║       Testing Agent from /nice/ folder                     ║
╚════════════════════════════════════════════════════════════╝

ℹ Agent ID: 91e70681-def8-4600-8a30-d037c1b51870
ℹ Endpoint: http://0.0.0.0:8333
ℹ Using API Key: rau_1d8e1d71edfeb4...
✓ OPENAI_API_KEY is set

============================================================
Test 1: Get Agent Architecture
============================================================

✓ Client created successfully
✓ Architecture retrieved

Available Entrypoints:
  • agno_print_response → agent_print_response (simple_assistant.py)
  • agno_print_response_stream → agent_print_response_stream (simple_assistant.py)

✓ Test 1 PASSED

[... more tests ...]

============================================================
Summary
============================================================

PHP SDK Implementation Status:

✓ Client initialization
✓ Architecture retrieval
✓ Authentication (Bearer token)
✓ Error handling with suggestions
✓ Entrypoint validation
✓ Run vs RunStream guardrails

All systems ready! Agent execution should work.
```

## Troubleshooting

### Issue: "INTERNAL_ERROR" or "An internal server error occurred"

**Cause**: Missing OpenAI API key

**Solution**:
```bash
export OPENAI_API_KEY='your-key-here'
cd /home/nihal/Desktop/github_repos/runagent/nice
runagent stop
runagent start
```

### Issue: "Not authenticated"

**Cause**: Missing or invalid RunAgent API key

**Solution**: The API key is auto-configured. If you see this, check:
```bash
sqlite3 ~/.runagent/runagent_local.db "SELECT value FROM user_metadata WHERE key='api_key';"
```

### Issue: "Connection refused"

**Cause**: Agent not running

**Solution**:
```bash
cd /home/nihal/Desktop/github_repos/runagent/nice
runagent start
```

### Issue: "Composer not found"

**Solution**:
```bash
curl -sS https://getcomposer.org/installer | php
sudo mv composer.phar /usr/local/bin/composer
```

### Issue: "PHP not found"

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install php8.2-cli php8.2-curl php8.2-mbstring

# Or use Docker
cd /home/nihal/Desktop/github_repos/runagent/runagent-php
./run-tests.sh
```

## SDK Checklist Status

✅ All items from `sdk_checklist.md` are implemented:

- [x] Client initialization with required parameters
- [x] Configuration precedence (explicit > env > defaults)
- [x] Local agent connection with host/port
- [x] Authentication with Bearer token
- [x] Architecture endpoint with envelope format
- [x] Entrypoint validation
- [x] HTTP `run()` for non-streaming
- [x] WebSocket `runStream()` for streaming
- [x] Error handling with structured errors
- [x] Run vs runStream guardrails
- [x] Extra params handling

## Next Steps

1. ✅ Set `OPENAI_API_KEY` environment variable
2. ✅ Restart your agent
3. ✅ Run `php examples/nice_agent_test.php`
4. ✅ Try `basic_example_updated.php` and `streaming_example_updated.php`
5. ✅ Update `sdk_checklist.md` to mark PHP SDK as complete

## Files Created

- `examples/basic_example_updated.php` - Basic usage (like Flutter example)
- `examples/streaming_example_updated.php` - Streaming usage
- `examples/nice_agent_test.php` - Comprehensive test for your agent
- `NICE_AGENT_GUIDE.md` - This guide
- `PHP_SDK_TEST_RESULTS.md` - Detailed test results
