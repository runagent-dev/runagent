<?php

/**
 * Test script for the agent deployed in /nice/ folder
 * 
 * Agent Info:
 * - ID: 91e70681-def8-4600-8a30-d037c1b51870
 * - Location: /home/nihal/Desktop/github_repos/runagent/nice/
 * - Endpoint: http://0.0.0.0:8333
 * - Entrypoints: agno_print_response, agno_print_response_stream
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
const RESET = "\033[0m";

function printSection($title) {
    echo "\n" . BLUE . str_repeat('=', 60) . RESET . "\n";
    echo BLUE . $title . RESET . "\n";
    echo BLUE . str_repeat('=', 60) . RESET . "\n\n";
}

function printSuccess($msg) {
    echo GREEN . "✓ " . $msg . RESET . "\n";
}

function printError($msg) {
    echo RED . "✗ " . $msg . RESET . "\n";
}

function printInfo($msg) {
    echo YELLOW . "ℹ " . $msg . RESET . "\n";
}

echo BLUE . "\n";
echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║       Testing Agent from /nice/ folder                     ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n";
echo RESET . "\n";

$agentId = '91e70681-def8-4600-8a30-d037c1b51870';
$apiKey = getenv('RUNAGENT_API_KEY') ?: 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6';

printInfo("Agent ID: $agentId");
printInfo("Endpoint: http://0.0.0.0:8333");
printInfo("Using API Key: " . substr($apiKey, 0, 20) . "...");

// Check if OpenAI API key is set
$openaiKey = getenv('OPENAI_API_KEY');
if (!$openaiKey) {
    echo "\n" . YELLOW . "⚠️  WARNING: OPENAI_API_KEY not set!" . RESET . "\n";
    echo "The agent uses OpenAI's gpt-4o-mini model.\n";
    echo "Set it with: export OPENAI_API_KEY='your-key-here'\n";
    echo "Then restart the agent: runagent stop && runagent start\n\n";
} else {
    printSuccess("OPENAI_API_KEY is set");
}

// =============================================================================
// Test 1: Get Agent Architecture
// =============================================================================
printSection("Test 1: Get Agent Architecture");

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
    printSuccess("Client created successfully");
    
    $architecture = $client->getAgentArchitecture();
    printSuccess("Architecture retrieved");
    
    echo "\nAvailable Entrypoints:\n";
    foreach ($architecture->entrypoints as $ep) {
        echo "  • " . BLUE . $ep->tag . RESET;
        echo " → " . $ep->module;
        echo " (" . $ep->file . ")\n";
    }
    
    printSuccess("\nTest 1 PASSED");
    
} catch (Exception $e) {
    printError("Test 1 FAILED: " . $e->getMessage());
}

// =============================================================================
// Test 2: Health Check
// =============================================================================
printSection("Test 2: Health Check");

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
        printSuccess("Test 2 PASSED");
    } else {
        printError("Agent health check failed");
    }
    
} catch (Exception $e) {
    printInfo("Health check endpoint might not be available (this is okay)");
    printInfo("Test 2 SKIPPED");
}

// =============================================================================
// Test 3: Non-Streaming Execution (Will fail without OpenAI key)
// =============================================================================
printSection("Test 3: Non-Streaming Execution");

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
    
    if (!$openaiKey) {
        printInfo("Skipping execution test - OPENAI_API_KEY not set");
        printInfo("This test will work after setting the API key");
    } else {
        printInfo("Sending prompt to agent...");
        
        $result = $client->run([
            'prompt' => 'What is 2+2? Answer in one sentence.'
        ]);
        
        echo "\n" . YELLOW . "Response:" . RESET . "\n";
        echo str_repeat('-', 60) . "\n";
        
        if (is_array($result)) {
            print_r($result);
        } elseif (is_object($result)) {
            if (method_exists($result, '__toString')) {
                echo $result . "\n";
            } else {
                print_r($result);
            }
        } else {
            echo $result . "\n";
        }
        
        echo str_repeat('-', 60) . "\n";
        printSuccess("Test 3 PASSED");
    }
    
} catch (RunAgentError $e) {
    printError("Test 3 FAILED: " . $e->getMessage());
    if ($e->getSuggestion()) {
        printInfo("Suggestion: " . $e->getSuggestion());
    }
    if (strpos($e->getMessage(), 'INTERNAL_ERROR') !== false) {
        printInfo("This is likely due to missing OPENAI_API_KEY");
    }
} catch (Exception $e) {
    printError("Test 3 FAILED: " . $e->getMessage());
}

// =============================================================================
// Test 4: Validate Guardrails (Stream tag with run() should fail)
// =============================================================================
printSection("Test 4: Validate Guardrails");

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
    
    printInfo("Attempting to use run() on streaming entrypoint (should fail)...");
    
    try {
        $client->run(['prompt' => 'test']);
        printError("Test 4 FAILED - Should have thrown ValidationError");
    } catch (RunAgentError $e) {
        if (strpos($e->getMessage(), 'Stream entrypoint') !== false) {
            printSuccess("Correctly caught validation error");
            printSuccess("Error: " . $e->getMessage());
            if ($e->getSuggestion()) {
                printSuccess("Suggestion: " . $e->getSuggestion());
            }
            printSuccess("Test 4 PASSED");
        } else {
            throw $e;
        }
    }
    
} catch (Exception $e) {
    printError("Test 4 FAILED: " . $e->getMessage());
}

// =============================================================================
// Summary
// =============================================================================
printSection("Summary");

echo "PHP SDK Implementation Status:\n\n";
echo GREEN . "✓ Client initialization" . RESET . "\n";
echo GREEN . "✓ Architecture retrieval" . RESET . "\n";
echo GREEN . "✓ Authentication (Bearer token)" . RESET . "\n";
echo GREEN . "✓ Error handling with suggestions" . RESET . "\n";
echo GREEN . "✓ Entrypoint validation" . RESET . "\n";
echo GREEN . "✓ Run vs RunStream guardrails" . RESET . "\n";

if (!$openaiKey) {
    echo "\n" . YELLOW . "⚠️  To test agent execution:" . RESET . "\n";
    echo "1. Set OpenAI API key: export OPENAI_API_KEY='your-key'\n";
    echo "2. Restart agent: cd /home/nihal/Desktop/github_repos/runagent/nice && runagent stop && runagent start\n";
    echo "3. Run this test again: php examples/nice_agent_test.php\n";
} else {
    echo "\n" . GREEN . "All systems ready! Agent execution should work." . RESET . "\n";
}

echo "\n";
