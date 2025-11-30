<?php

/**
 * Test script for deployed agent 91e70681-def8-4600-8a30-d037c1b51870
 * 
 * This script tests the PHP SDK against a deployed RunAgent instance.
 * It validates:
 * - Client initialization with local configuration
 * - Non-streaming entrypoint (agno_print_response)
 * - Streaming entrypoint (agno_print_response_stream)
 * - Error handling
 * - Health checks
 */

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

// ANSI color codes for terminal output
const COLOR_GREEN = "\033[0;32m";
const COLOR_RED = "\033[0;31m";
const COLOR_YELLOW = "\033[0;33m";
const COLOR_BLUE = "\033[0;34m";
const COLOR_RESET = "\033[0m";

function printSection($title) {
    echo "\n" . COLOR_BLUE . "========================================" . COLOR_RESET . "\n";
    echo COLOR_BLUE . $title . COLOR_RESET . "\n";
    echo COLOR_BLUE . "========================================" . COLOR_RESET . "\n\n";
}

function printSuccess($message) {
    echo COLOR_GREEN . "✓ " . $message . COLOR_RESET . "\n";
}

function printError($message) {
    echo COLOR_RED . "✗ " . $message . COLOR_RESET . "\n";
}

function printInfo($message) {
    echo COLOR_YELLOW . "ℹ " . $message . COLOR_RESET . "\n";
}

// Agent configuration
$agentId = '91e70681-def8-4600-8a30-d037c1b51870';
$localHost = '0.0.0.0';
$localPort = 8333;
$apiKey = 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6';

// Test counter
$totalTests = 0;
$passedTests = 0;
$failedTests = 0;

echo COLOR_BLUE . "\n";
echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║       RunAgent PHP SDK - Deployed Agent Test Suite        ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n";
echo COLOR_RESET . "\n";

printInfo("Testing agent: $agentId");
printInfo("Local endpoint: http://$localHost:$localPort");
echo "\n";

// =============================================================================
// TEST 1: Non-Streaming Entrypoint
// =============================================================================
printSection("TEST 1: Non-Streaming Entrypoint (agno_print_response)");

try {
    $totalTests++;
    
    printInfo("Creating client for non-streaming entrypoint...");
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response',
        local: true,
        host: $localHost,
        port: $localPort,
        apiKey: $apiKey
    );
    
    $client = RunAgentClient::create($config);
    printSuccess("Client created successfully");
    
    // Health check
    printInfo("Performing health check...");
    if ($client->healthCheck()) {
        printSuccess("Agent is healthy");
    } else {
        throw new Exception("Agent health check failed");
    }
    
    // Get architecture
    printInfo("Fetching agent architecture...");
    $architecture = $client->getAgentArchitecture();
    printSuccess("Architecture retrieved: " . count($architecture->entrypoints) . " entrypoints found");
    
    foreach ($architecture->entrypoints as $ep) {
        echo "  - Tag: {$ep->tag}, Module: {$ep->module}\n";
    }
    
    // Run agent
    printInfo("\nRunning agent with prompt: 'What is 2+2?'");
    $result = $client->run([
        'prompt' => 'What is 2+2? Answer in one short sentence.'
    ]);
    
    printSuccess("Agent executed successfully");
    echo "\n" . COLOR_YELLOW . "Response:" . COLOR_RESET . "\n";
    echo str_repeat("-", 60) . "\n";
    
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
    
    echo str_repeat("-", 60) . "\n";
    
    $passedTests++;
    printSuccess("TEST 1 PASSED");
    
} catch (RunAgentError $e) {
    $failedTests++;
    printError("TEST 1 FAILED");
    printError("Error [{$e->getErrorCode()}]: {$e->getMessage()}");
    if ($e->getSuggestion() !== null) {
        printInfo("Suggestion: {$e->getSuggestion()}");
    }
} catch (Exception $e) {
    $failedTests++;
    printError("TEST 1 FAILED");
    printError("Unexpected error: {$e->getMessage()}");
    printError("Stack trace: " . $e->getTraceAsString());
}

// =============================================================================
// TEST 2: Streaming Entrypoint
// =============================================================================
printSection("TEST 2: Streaming Entrypoint (agno_print_response_stream)");

try {
    $totalTests++;
    
    printInfo("Creating client for streaming entrypoint...");
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response_stream',
        local: true,
        host: $localHost,
        port: $localPort,
        apiKey: $apiKey
    );
    
    $client = RunAgentClient::create($config);
    printSuccess("Client created successfully");
    
    // Run streaming agent
    printInfo("Running streaming agent with prompt: 'Count from 1 to 5'");
    echo "\n" . COLOR_YELLOW . "Streaming response:" . COLOR_RESET . "\n";
    echo str_repeat("-", 60) . "\n";
    
    $chunkCount = 0;
    foreach ($client->runStream(['prompt' => 'Count from 1 to 5. Be brief.']) as $chunk) {
        $chunkCount++;
        
        if (is_array($chunk)) {
            if (isset($chunk['content'])) {
                echo $chunk['content'];
            } else {
                print_r($chunk);
            }
        } elseif (is_object($chunk)) {
            if (method_exists($chunk, '__toString')) {
                echo $chunk;
            } else {
                print_r($chunk);
            }
        } else {
            echo $chunk;
        }
        
        flush();
    }
    
    echo "\n" . str_repeat("-", 60) . "\n";
    printSuccess("Received $chunkCount chunks");
    
    $passedTests++;
    printSuccess("TEST 2 PASSED");
    
} catch (RunAgentError $e) {
    $failedTests++;
    printError("TEST 2 FAILED");
    printError("Error [{$e->getErrorCode()}]: {$e->getMessage()}");
    if ($e->getSuggestion() !== null) {
        printInfo("Suggestion: {$e->getSuggestion()}");
    }
} catch (Exception $e) {
    $failedTests++;
    printError("TEST 2 FAILED");
    printError("Unexpected error: {$e->getMessage()}");
    printError("Stack trace: " . $e->getTraceAsString());
}

// =============================================================================
// TEST 3: Error Handling - Wrong Entrypoint Type
// =============================================================================
printSection("TEST 3: Error Handling - Using run() on stream entrypoint");

try {
    $totalTests++;
    
    printInfo("Creating client with streaming tag...");
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response_stream',
        local: true,
        host: $localHost,
        port: $localPort,
        apiKey: $apiKey
    );
    
    $client = RunAgentClient::create($config);
    
    printInfo("Attempting to call run() on streaming entrypoint (should fail)...");
    try {
        $client->run(['prompt' => 'This should fail']);
        $failedTests++;
        printError("TEST 3 FAILED - Expected ValidationError but got success");
    } catch (RunAgentError $e) {
        if (strpos($e->getMessage(), 'Stream entrypoint') !== false) {
            printSuccess("Correctly caught validation error: " . $e->getMessage());
            $passedTests++;
            printSuccess("TEST 3 PASSED");
        } else {
            throw $e;
        }
    }
    
} catch (Exception $e) {
    $failedTests++;
    printError("TEST 3 FAILED");
    printError("Unexpected error: {$e->getMessage()}");
}

// =============================================================================
// TEST 4: Error Handling - Wrong Entrypoint Type (Reverse)
// =============================================================================
printSection("TEST 4: Error Handling - Using runStream() on non-stream entrypoint");

try {
    $totalTests++;
    
    printInfo("Creating client with non-streaming tag...");
    $config = new RunAgentClientConfig(
        agentId: $agentId,
        entrypointTag: 'agno_print_response',
        local: true,
        host: $localHost,
        port: $localPort,
        apiKey: $apiKey
    );
    
    $client = RunAgentClient::create($config);
    
    printInfo("Attempting to call runStream() on non-streaming entrypoint (should fail)...");
    try {
        foreach ($client->runStream(['prompt' => 'This should fail']) as $chunk) {
            // Should not reach here
        }
        $failedTests++;
        printError("TEST 4 FAILED - Expected ValidationError but got success");
    } catch (RunAgentError $e) {
        if (strpos($e->getMessage(), 'Non-stream entrypoint') !== false) {
            printSuccess("Correctly caught validation error: " . $e->getMessage());
            $passedTests++;
            printSuccess("TEST 4 PASSED");
        } else {
            throw $e;
        }
    }
    
} catch (Exception $e) {
    $failedTests++;
    printError("TEST 4 FAILED");
    printError("Unexpected error: {$e->getMessage()}");
}

// =============================================================================
// TEST 5: Invalid Entrypoint
// =============================================================================
printSection("TEST 5: Error Handling - Invalid entrypoint tag");

try {
    $totalTests++;
    
    printInfo("Creating client with invalid entrypoint tag...");
    try {
        $config = new RunAgentClientConfig(
            agentId: $agentId,
            entrypointTag: 'nonexistent_entrypoint',
            local: true,
            host: $localHost,
            port: $localPort,
            apiKey: $apiKey
        );
        
        $client = RunAgentClient::create($config);
        $failedTests++;
        printError("TEST 5 FAILED - Expected ValidationError but client created successfully");
    } catch (RunAgentError $e) {
        if (strpos($e->getMessage(), 'not found') !== false) {
            printSuccess("Correctly caught validation error: " . $e->getMessage());
            if ($e->getSuggestion() !== null) {
                printInfo("Available entrypoints shown: " . $e->getSuggestion());
            }
            $passedTests++;
            printSuccess("TEST 5 PASSED");
        } else {
            throw $e;
        }
    }
    
} catch (Exception $e) {
    $failedTests++;
    printError("TEST 5 FAILED");
    printError("Unexpected error: {$e->getMessage()}");
}

// =============================================================================
// SUMMARY
// =============================================================================
printSection("TEST SUMMARY");

echo "Total tests:  $totalTests\n";
echo COLOR_GREEN . "Passed:       $passedTests" . COLOR_RESET . "\n";

if ($failedTests > 0) {
    echo COLOR_RED . "Failed:       $failedTests" . COLOR_RESET . "\n";
} else {
    echo "Failed:       $failedTests\n";
}

$successRate = $totalTests > 0 ? round(($passedTests / $totalTests) * 100, 1) : 0;
echo "Success rate: $successRate%\n\n";

if ($failedTests === 0) {
    echo COLOR_GREEN;
    echo "╔════════════════════════════════════════════════════════════╗\n";
    echo "║                  ALL TESTS PASSED! ✓                       ║\n";
    echo "╚════════════════════════════════════════════════════════════╝\n";
    echo COLOR_RESET . "\n";
    exit(0);
} else {
    echo COLOR_RED;
    echo "╔════════════════════════════════════════════════════════════╗\n";
    echo "║               SOME TESTS FAILED ✗                          ║\n";
    echo "╚════════════════════════════════════════════════════════════╝\n";
    echo COLOR_RESET . "\n";
    exit(1);
}
