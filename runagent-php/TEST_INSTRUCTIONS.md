# PHP SDK Testing Instructions

This guide will help you test the RunAgent PHP SDK against your deployed agent.

## Prerequisites

1. **PHP 8.0 or higher**
   ```bash
   php --version
   ```

2. **Composer** (PHP dependency manager)
   ```bash
   curl -sS https://getcomposer.org/installer | php
   sudo mv composer.phar /usr/local/bin/composer
   ```

3. **Required PHP extensions:**
   - curl
   - json
   - mbstring
   - sockets (for WebSocket streaming)

## Installation

1. Navigate to the PHP SDK directory:
   ```bash
   cd /home/nihal/Desktop/github_repos/runagent/runagent-php
   ```

2. Install dependencies:
   ```bash
   composer install
   ```

## Running the Tests

### Quick Test (Deployed Agent)

Your agent is already running at:
- **Agent ID:** `91e70681-def8-4600-8a30-d037c1b51870`
- **Endpoint:** `http://0.0.0.0:8333`
- **Entrypoints:**
  - `agno_print_response` (non-streaming)
  - `agno_print_response_stream` (streaming)

Run the comprehensive test suite:

```bash
php examples/test_deployed_agent.php
```

### What the Test Suite Covers

The test script validates the following SDK checklist items:

✅ **Client Initialization**
- Constructor with required parameters (agent_id, entrypoint_tag)
- Local mode with explicit host/port
- Configuration precedence

✅ **Non-Streaming Execution (`run()`)**
- POST /api/v1/agents/{id}/run
- Proper payload formatting
- Response deserialization
- Health checks
- Architecture retrieval

✅ **Streaming Execution (`runStream()`)**
- WebSocket connection
- Stream chunk iteration
- Proper message handling

✅ **Error Handling**
- Validation errors for wrong entrypoint types
- Clear error messages with suggestions
- Structured error format (code, message, suggestion, details)

✅ **Guardrails**
- Enforces stream tags only work with `runStream()`
- Enforces non-stream tags only work with `run()`
- Lists available entrypoints on mismatch

### Expected Output

If everything works correctly, you should see:

```
╔════════════════════════════════════════════════════════════╗
║       RunAgent PHP SDK - Deployed Agent Test Suite        ║
╚════════════════════════════════════════════════════════════╝

ℹ Testing agent: 91e70681-def8-4600-8a30-d037c1b51870
ℹ Local endpoint: http://0.0.0.0:8333

========================================
TEST 1: Non-Streaming Entrypoint (agno_print_response)
========================================

✓ Client created successfully
✓ Agent is healthy
✓ Architecture retrieved: 2 entrypoints found
  - Tag: agno_print_response, Module: agent_print_response
  - Tag: agno_print_response_stream, Module: agent_print_response_stream
✓ Agent executed successfully

Response:
------------------------------------------------------------
[Agent response here]
------------------------------------------------------------
✓ TEST 1 PASSED

[... more tests ...]

========================================
TEST SUMMARY
========================================
Total tests:  5
Passed:       5
Failed:       0
Success rate: 100.0%

╔════════════════════════════════════════════════════════════╗
║                  ALL TESTS PASSED! ✓                       ║
╚════════════════════════════════════════════════════════════╝
```

## Manual Testing

### Test Non-Streaming Entrypoint

```php
<?php
require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;

$config = new RunAgentClientConfig(
    agentId: '91e70681-def8-4600-8a30-d037c1b51870',
    entrypointTag: 'agno_print_response',
    local: true,
    host: '0.0.0.0',
    port: 8333
);

$client = RunAgentClient::create($config);

$result = $client->run([
    'prompt' => 'What is the capital of France?'
]);

print_r($result);
```

### Test Streaming Entrypoint

```php
<?php
require_once 'vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;

$config = new RunAgentClientConfig(
    agentId: '91e70681-def8-4600-8a30-d037c1b51870',
    entrypointTag: 'agno_print_response_stream',
    local: true,
    host: '0.0.0.0',
    port: 8333
);

$client = RunAgentClient::create($config);

foreach ($client->runStream(['prompt' => 'Tell me a short story']) as $chunk) {
    if (is_array($chunk) && isset($chunk['content'])) {
        echo $chunk['content'];
    } else {
        echo $chunk;
    }
    flush();
}
```

## Troubleshooting

### Issue: "composer: command not found"
**Solution:** Install Composer first (see Prerequisites)

### Issue: "PHP Fatal error: Uncaught Error: Class 'RunAgent\Client\RunAgentClient' not found"
**Solution:** Run `composer install` to install dependencies

### Issue: "Connection refused"
**Solution:** Make sure your agent is running:
```bash
cd /home/nihal/Desktop/github_repos/runagent/nice
runagent start
```

### Issue: "Entrypoint not found"
**Solution:** The test script will show available entrypoints. Make sure you're using:
- `agno_print_response` for non-streaming
- `agno_print_response_stream` for streaming

### Issue: WebSocket connection fails
**Solution:** Ensure the `sockets` PHP extension is installed:
```bash
sudo apt-get install php-sockets  # Ubuntu/Debian
# or
sudo yum install php-sockets      # CentOS/RHEL
```

## SDK Checklist Validation

This test suite validates the following items from `sdk_checklist.md`:

- [x] Client initialization with required parameters
- [x] Configuration precedence (explicit > env > defaults)
- [x] Local agent connection with host/port
- [x] HTTP `run()` semantics
- [x] WebSocket `runStream()` semantics
- [x] Error handling with structured errors
- [x] Architecture endpoint contract
- [x] Entrypoint validation with helpful messages
- [x] Run vs. runStream guardrails
- [x] Health check functionality

## Next Steps

After successful testing:

1. ✅ Mark PHP SDK items as complete in `sdk_checklist.md`
2. Test with different agent types (if available)
3. Test error scenarios (invalid API keys, network issues)
4. Consider adding remote agent tests with API keys
5. Add to CI/CD pipeline

## Support

If you encounter issues:
1. Check the error message and suggestion provided
2. Verify agent is running: `runagent status`
3. Check agent logs for backend errors
4. Review the SDK source code in `src/`
