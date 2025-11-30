# Quick Start: Testing PHP SDK with Your Deployed Agent

## ⚡ Quick Test (Using Docker)

Your agent is running at `http://0.0.0.0:8333` with ID `91e70681-def8-4600-8a30-d037c1b51870`.

### Option 1: Docker (Recommended - No PHP installation needed)

```bash
cd /home/nihal/Desktop/github_repos/runagent/runagent-php
./run-tests.sh
```

This will:
1. Build a Docker image with PHP 8.2 and all dependencies
2. Run the comprehensive test suite
3. Test both streaming and non-streaming entrypoints
4. Validate error handling

### Option 2: Local PHP (If you have PHP 8.0+ installed)

```bash
cd /home/nihal/Desktop/github_repos/runagent/runagent-php

# Install dependencies
composer install

# Run tests
php examples/test_deployed_agent.php
```

## 📋 What Gets Tested

The test suite validates:

1. **✅ Non-Streaming Execution**
   - Connects to `agno_print_response` entrypoint
   - Sends prompt and receives response
   - Validates response format

2. **✅ Streaming Execution**
   - Connects to `agno_print_response_stream` entrypoint
   - Receives and displays streaming chunks
   - Counts total chunks received

3. **✅ Error Handling**
   - Tests using `run()` on streaming entrypoint (should fail)
   - Tests using `runStream()` on non-streaming entrypoint (should fail)
   - Tests invalid entrypoint name
   - Validates error messages and suggestions

4. **✅ Architecture Validation**
   - Fetches agent architecture
   - Lists available entrypoints
   - Validates entrypoint configuration

5. **✅ Health Checks**
   - Pings agent to ensure it's responsive

## 📊 Expected Results

```
╔════════════════════════════════════════════════════════════╗
║       RunAgent PHP SDK - Deployed Agent Test Suite        ║
╚════════════════════════════════════════════════════════════╝

ℹ Testing agent: 91e70681-def8-4600-8a30-d037c1b51870
ℹ Local endpoint: http://0.0.0.0:8333

========================================
TEST 1: Non-Streaming Entrypoint
========================================
✓ Client created successfully
✓ Agent is healthy
✓ Architecture retrieved: 2 entrypoints found
✓ Agent executed successfully
✓ TEST 1 PASSED

========================================
TEST 2: Streaming Entrypoint
========================================
✓ Client created successfully
✓ Received X chunks
✓ TEST 2 PASSED

[... 3 more tests ...]

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

## 🔍 Troubleshooting

### Docker not found
```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Agent not running
```bash
cd /home/nihal/Desktop/github_repos/runagent/nice
runagent start
```

### Connection refused
Make sure the agent is listening on `0.0.0.0:8333`:
```bash
# Check if agent is running
curl http://0.0.0.0:8333/health

# Or check agent status
runagent status
```

## 🎯 SDK Checklist Verification

This test validates the following from `sdk_checklist.md`:

- [x] Client initialization with agent_id and entrypoint_tag
- [x] Local mode with explicit host/port  
- [x] Configuration precedence (explicit args)
- [x] HTTP `run()` for non-streaming
- [x] WebSocket `runStream()` for streaming
- [x] Architecture endpoint parsing
- [x] Entrypoint validation
- [x] Error handling with codes and suggestions
- [x] Run vs runStream guardrails
- [x] Health check functionality

## 📝 Next Steps

After successful testing:

1. Update `sdk_checklist.md` to mark PHP SDK items as complete
2. Test with different prompts and inputs
3. Test remote deployment (with API keys)
4. Add to CI/CD pipeline
5. Review error handling edge cases

## 💡 Manual Testing Examples

### Quick Non-Streaming Test
```bash
cd /home/nihal/Desktop/github_repos/runagent/runagent-php

# Create a quick test file
cat > test_quick.php << 'EOF'
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
$result = $client->run(['prompt' => 'What is 2+2?']);
print_r($result);
EOF

php test_quick.php
```

### Quick Streaming Test
```bash
cat > test_stream.php << 'EOF'
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

foreach ($client->runStream(['prompt' => 'Count to 3']) as $chunk) {
    echo json_encode($chunk) . "\n";
}
EOF

php test_stream.php
```

## 📚 Documentation

For more details, see:
- `TEST_INSTRUCTIONS.md` - Comprehensive testing guide
- `README.md` - PHP SDK documentation
- `../sdk_checklist.md` - SDK implementation requirements
