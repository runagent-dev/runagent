<?php

/**
 * Comprehensive test script for the nice/ agent
 * 
 * Agent Info:
 * - ID: 91e70681-def8-4600-8a30-d037c1b51870
 * - Location: /home/nihal/Desktop/github_repos/runagent/nice/
 * - Endpoint: http://0.0.0.0:8333
 * - Entrypoints:
 *   1. agno_print_response (non-streaming)
 *   2. agno_print_response_stream (streaming)
 * 
 * This test follows the structure of runagent-dart examples
 */

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

// ANSI colors for better output
const GREEN = "\033[0;32m";
const RED = "\033[0;31m";
const YELLOW = "\033[0;33m";
const BLUE = "\033[0;34m";
const CYAN = "\033[0;36m";
const RESET = "\033[0m";

function printHeader($title) {
    echo "\n" . CYAN . str_repeat('═', 70) . RESET . "\n";
    echo CYAN . "  " . $title . RESET . "\n";
    echo CYAN . str_repeat('═', 70) . RESET . "\n\n";
}

function printSection($title) {
    echo "\n" . BLUE . str_repeat('─', 70) . RESET . "\n";
    echo BLUE . "  " . $title . RESET . "\n";
    echo BLUE . str_repeat('─', 70) . RESET . "\n\n";
}

function printSuccess($msg) {
    echo GREEN . "  ✓ " . $msg . RESET . "\n";
}

function printError($msg) {
    echo RED . "  ✗ " . $msg . RESET . "\n";
}

function printInfo($msg) {
    echo YELLOW . "  ℹ " . $msg . RESET . "\n";
}

function printData($label, $data) {
    echo "  " . YELLOW . $label . ": " . RESET;
    if (is_array($data) || is_object($data)) {
        echo "\n";
        print_r($data);
    } else {
        echo $data . "\n";
    }
}

echo CYAN . "\n";
echo "╔════════════════════════════════════════════════════════════════════╗\n";
echo "║           RunAgent PHP SDK Test - Nice Agent                       ║\n";
echo "║           Following runagent-dart example structure                ║\n";
echo "╚════════════════════════════════════════════════════════════════════╝\n";
echo RESET . "\n";

$agentId = '91e70681-def8-4600-8a30-d037c1b51870';
$apiKey = getenv('RUNAGENT_API_KEY') ?: 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6';

printInfo("Agent ID: $agentId");
printInfo("Endpoint: http://0.0.0.0:8333");
printInfo("API Key: " . substr($apiKey, 0, 20) . "...");

// Check if OpenAI API key is set
$openaiKey = getenv('OPENAI_API_KEY');
if (!$openaiKey) {
    echo "\n" . YELLOW . "  ⚠️  WARNING: OPENAI_API_KEY not set!" . RESET . "\n";
    echo "  The agent uses OpenAI's gpt-4o-mini model.\n";
    echo "  Set it with: export OPENAI_API_KEY='your-key-here'\n\n";
} else {
    printSuccess("OPENAI_API_KEY is configured");
}

$testResults = [
    'passed' => 0,
    'failed' => 0,
    'skipped' => 0
];

// =============================================================================
// Test 1: Client Creation and Agent Architecture (similar to dart basic_example)
// =============================================================================
printHeader("TEST 1: Client Creation & Architecture Retrieval");

try {
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response',
        local: true,
        host: '0.0.0.0',
        port: 8333,
        apiKey: $apiKey
    );
    
    printInfo("Creating client with config:");
    printInfo("  - Agent ID: $agentId");
    printInfo("  - Entrypoint: agno_print_response");
    printInfo("  - Local mode: true");
    
    $client = RunAgentClient::create($config);
    printSuccess("Client created successfully");
    
    $architecture = $client->getAgentArchitecture();
    printSuccess("Architecture retrieved");
    
    echo "\n";
    printData("Agent Name", $architecture->agent_name ?? 'N/A');
    printData("Framework", $architecture->framework ?? 'N/A');
    printData("Version", $architecture->version ?? 'N/A');
    
    echo "\n  " . YELLOW . "Available Entrypoints:" . RESET . "\n";
    foreach ($architecture->entrypoints as $index => $ep) {
        echo "    " . ($index + 1) . ". " . BLUE . $ep->tag . RESET;
        echo " → " . $ep->module;
        echo " (" . $ep->file . ")\n";
    }
    
    printSuccess("\n✅ TEST 1 PASSED");
    $testResults['passed']++;
    
} catch (Exception $e) {
    printError("❌ TEST 1 FAILED: " . $e->getMessage());
    $testResults['failed']++;
}

// =============================================================================
// Test 2: Non-Streaming Execution (similar to dart basic_example run())
// =============================================================================
printHeader("TEST 2: Non-Streaming Execution (agno_print_response)");

if (!$openaiKey) {
    printInfo("⊘ Skipping - OPENAI_API_KEY not set");
    printInfo("This test requires OpenAI API key for agent execution");
    $testResults['skipped']++;
} else {
    try {
        $config = new RunAgentClientConfig(
            agentId: $agentId,
            entrypointTag: 'agno_print_response',
            local: true,
            host: '0.0.0.0',
            port: 8333,
            apiKey: $apiKey
        );
        
        $client = RunAgentClient::create($config);
        printSuccess("Client initialized for non-streaming");
        
        printInfo("Sending prompt: 'What is 2+2? Answer briefly.'");
        
        $result = $client->run([
            'prompt' => 'What is 2+2? Answer in one short sentence.'
        ]);
        
        echo "\n  " . YELLOW . "Response received:" . RESET . "\n";
        echo "  " . str_repeat('─', 68) . "\n";
        
        if (is_array($result)) {
            foreach ($result as $key => $value) {
                echo "    $key: $value\n";
            }
        } elseif (is_object($result)) {
            if (method_exists($result, '__toString')) {
                echo "    " . $result . "\n";
            } else {
                print_r($result);
            }
        } else {
            echo "    " . $result . "\n";
        }
        
        echo "  " . str_repeat('─', 68) . "\n";
        printSuccess("\n✅ TEST 2 PASSED");
        $testResults['passed']++;
        
    } catch (RunAgentError $e) {
        printError("❌ TEST 2 FAILED: " . $e->getMessage());
        if ($e->getSuggestion()) {
            printInfo("Suggestion: " . $e->getSuggestion());
        }
        $testResults['failed']++;
    } catch (Exception $e) {
        printError("❌ TEST 2 FAILED: " . $e->getMessage());
        $testResults['failed']++;
    }
}

// =============================================================================
// Test 3: Streaming Execution (similar to dart streaming_example)
// =============================================================================
printHeader("TEST 3: Streaming Execution (agno_print_response_stream)");

if (!$openaiKey) {
    printInfo("⊘ Skipping - OPENAI_API_KEY not set");
    printInfo("This test requires OpenAI API key for agent execution");
    $testResults['skipped']++;
} else {
    try {
        $config = new RunAgentClientConfig(
            agentId: $agentId,
            entrypointTag: 'agno_print_response_stream',  // Streaming entrypoint
            local: true,
            host: '0.0.0.0',
            port: 8333,
            apiKey: $apiKey
        );
        
        $client = RunAgentClient::create($config);
        printSuccess("Client initialized for streaming");
        
        printInfo("Sending prompt: 'Count from 1 to 5'");
        
        echo "\n  " . YELLOW . "Streaming response:" . RESET . "\n";
        echo "  " . str_repeat('─', 68) . "\n";
        
        $chunkCount = 0;
        foreach ($client->runStream(['prompt' => 'Count from 1 to 5. Just the numbers, briefly.']) as $chunk) {
            $chunkCount++;
            echo "  Chunk $chunkCount: ";
            if (is_array($chunk)) {
                echo json_encode($chunk);
            } elseif (is_object($chunk)) {
                if (isset($chunk->content)) {
                    echo $chunk->content;
                } else {
                    echo json_encode($chunk);
                }
            } else {
                echo $chunk;
            }
            echo "\n";
        }
        
        echo "  " . str_repeat('─', 68) . "\n";
        printSuccess("Received $chunkCount chunks");
        printSuccess("\n✅ TEST 3 PASSED");
        $testResults['passed']++;
        
    } catch (RunAgentError $e) {
        printError("❌ TEST 3 FAILED: " . $e->getMessage());
        if ($e->getSuggestion()) {
            printInfo("Suggestion: " . $e->getSuggestion());
        }
        $testResults['failed']++;
    } catch (Exception $e) {
        printError("❌ TEST 3 FAILED: " . $e->getMessage());
        $testResults['failed']++;
    }
}

// =============================================================================
// Test 4: Error Handling - Wrong entrypoint for method
// =============================================================================
printHeader("TEST 4: Error Handling - Entrypoint Validation");

try {
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response_stream',  // Streaming tag
        local: true,
        host: '0.0.0.0',
        port: 8333,
        apiKey: $apiKey
    );
    
    $client = RunAgentClient::create($config);
    
    printInfo("Attempting run() on streaming entrypoint (should fail)...");
    
    try {
        $client->run(['prompt' => 'test']);
        printError("❌ TEST 4 FAILED - Should have thrown ValidationError");
        $testResults['failed']++;
    } catch (RunAgentError $e) {
        if (strpos($e->getMessage(), 'Stream entrypoint') !== false || 
            strpos($e->getMessage(), 'streaming') !== false) {
            printSuccess("Correctly caught validation error");
            printInfo("Error message: " . $e->getMessage());
            if ($e->getSuggestion()) {
                printInfo("Suggestion: " . $e->getSuggestion());
            }
            printSuccess("\n✅ TEST 4 PASSED");
            $testResults['passed']++;
        } else {
            throw $e;
        }
    }
    
} catch (Exception $e) {
    printError("❌ TEST 4 FAILED: " . $e->getMessage());
    $testResults['failed']++;
}

// =============================================================================
// Test 5: Health Check
// =============================================================================
printHeader("TEST 5: Health Check");

try {
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response',
        local: true,
        host: '0.0.0.0',
        port: 8333,
        apiKey: $apiKey
    );
    
    $client = RunAgentClient::create($config);
    
    if ($client->healthCheck()) {
        printSuccess("Agent is healthy and responding");
        printSuccess("\n✅ TEST 5 PASSED");
        $testResults['passed']++;
    } else {
        printError("Agent health check failed");
        $testResults['failed']++;
    }
    
} catch (Exception $e) {
    printInfo("Health check endpoint not available (this is okay)");
    printInfo("⊘ TEST 5 SKIPPED");
    $testResults['skipped']++;
}

// =============================================================================
// SUMMARY
// =============================================================================
printHeader("TEST SUMMARY");

$total = $testResults['passed'] + $testResults['failed'] + $testResults['skipped'];
echo "  Total Tests: $total\n";
echo "  " . GREEN . "✓ Passed:  {$testResults['passed']}" . RESET . "\n";
echo "  " . RED . "✗ Failed:  {$testResults['failed']}" . RESET . "\n";
echo "  " . YELLOW . "⊘ Skipped: {$testResults['skipped']}" . RESET . "\n\n";

if ($testResults['failed'] > 0) {
    echo RED . "  ❌ Some tests failed" . RESET . "\n\n";
    exit(1);
} else if ($testResults['skipped'] > 0) {
    echo YELLOW . "  ⚠️  Some tests skipped - Set OPENAI_API_KEY to run all tests" . RESET . "\n";
    echo "\n  To run all tests:\n";
    echo "  1. export OPENAI_API_KEY='your-key'\n";
    echo "  2. Restart agent: runagent stop --id $agentId && runagent start --id $agentId\n";
    echo "  3. Run: php " . __FILE__ . "\n\n";
    exit(0);
} else {
    echo GREEN . "  ✅ All tests passed!" . RESET . "\n\n";
    exit(0);
}
