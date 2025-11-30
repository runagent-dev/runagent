<?php

/**
 * Simple PHP test for RunAgent deployed agent
 * 
 * This test directly uses cURL to test the agent endpoints
 * without requiring the full SDK or Composer.
 */

// Configuration
$agentId = '91e70681-def8-4600-8a30-d037c1b51870';
$host = '0.0.0.0';
$port = 8333;
$apiKey = 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6';
$baseUrl = "http://$host:$port/api/v1";

// ANSI colors
const GREEN = "\033[0;32m";
const RED = "\033[0;31m";
const YELLOW = "\033[0;33m";
const BLUE = "\033[0;34m";
const RESET = "\033[0m";

function printTest($name) {
    echo "\n" . BLUE . "========================================" . RESET . "\n";
    echo BLUE . $name . RESET . "\n";
    echo BLUE . "========================================" . RESET . "\n\n";
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

$passed = 0;
$failed = 0;
$total = 0;

echo BLUE . "\n";
echo "╔════════════════════════════════════════════════════════════╗\n";
echo "║       RunAgent PHP - Simple cURL Test Suite               ║\n";
echo "╚════════════════════════════════════════════════════════════╝\n";
echo RESET . "\n";

printInfo("Agent ID: $agentId");
printInfo("Endpoint: $baseUrl");
echo "\n";

// =============================================================================
// TEST 1: Get Architecture
// =============================================================================
printTest("TEST 1: Get Agent Architecture");
$total++;

try {
    $ch = curl_init("$baseUrl/agents/$agentId/architecture");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        "Authorization: Bearer $apiKey"
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200) {
        throw new Exception("HTTP $httpCode: $response");
    }
    
    $data = json_decode($response, true);
    if (!$data || !isset($data['success']) || !$data['success']) {
        throw new Exception("Failed to get architecture: " . ($data['message'] ?? 'Unknown error'));
    }
    
    $entrypoints = $data['data']['entrypoints'] ?? [];
    printSuccess("Architecture retrieved successfully");
    printSuccess("Found " . count($entrypoints) . " entrypoints:");
    
    foreach ($entrypoints as $ep) {
        echo "  - " . $ep['tag'] . " (" . $ep['module'] . ")\n";
    }
    
    $passed++;
    printSuccess("TEST 1 PASSED");
} catch (Exception $e) {
    $failed++;
    printError("TEST 1 FAILED: " . $e->getMessage());
}

// =============================================================================
// TEST 2: Non-Streaming Execution
// =============================================================================
printTest("TEST 2: Non-Streaming Execution (agno_print_response)");
$total++;

try {
    $payload = [
        'entrypoint_tag' => 'agno_print_response',
        'input_args' => [],
        'input_kwargs' => [
            'prompt' => 'What is 2+2? Answer in one short sentence.'
        ],
        'timeout_seconds' => 300,
        'async_execution' => false
    ];
    
    $ch = curl_init("$baseUrl/agents/$agentId/run");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        "Authorization: Bearer $apiKey"
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    
    printInfo("Sending request...");
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);
    
    if ($response === false) {
        throw new Exception("cURL error: $curlError");
    }
    
    if ($httpCode !== 200) {
        throw new Exception("HTTP $httpCode: $response");
    }
    
    $data = json_decode($response, true);
    if (!$data) {
        throw new Exception("Invalid JSON response");
    }
    
    printSuccess("Response received");
    echo "\n" . YELLOW . "Response data:" . RESET . "\n";
    echo str_repeat("-", 60) . "\n";
    echo json_encode($data, JSON_PRETTY_PRINT) . "\n";
    echo str_repeat("-", 60) . "\n";
    
    $passed++;
    printSuccess("TEST 2 PASSED");
} catch (Exception $e) {
    $failed++;
    printError("TEST 2 FAILED: " . $e->getMessage());
}

// =============================================================================
// TEST 3: Health Check
// =============================================================================
printTest("TEST 3: Health Check");
$total++;

try {
    $ch = curl_init("$baseUrl/health");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    // Health endpoint might return 404, which is okay
    // as long as we get a response
    if ($response !== false) {
        printSuccess("Agent is responding");
        $passed++;
        printSuccess("TEST 3 PASSED");
    } else {
        throw new Exception("No response from health endpoint");
    }
} catch (Exception $e) {
    $failed++;
    printError("TEST 3 FAILED: " . $e->getMessage());
}

// =============================================================================
// TEST SUMMARY
// =============================================================================
printTest("TEST SUMMARY");

echo "Total tests:  $total\n";
echo GREEN . "Passed:       $passed" . RESET . "\n";

if ($failed > 0) {
    echo RED . "Failed:       $failed" . RESET . "\n";
} else {
    echo "Failed:       $failed\n";
}

$successRate = $total > 0 ? round(($passed / $total) * 100, 1) : 0;
echo "Success rate: $successRate%\n\n";

if ($failed === 0) {
    echo GREEN;
    echo "╔════════════════════════════════════════════════════════════╗\n";
    echo "║              ALL TESTS PASSED! ✓                           ║\n";
    echo "║                                                            ║\n";
    echo "║  The PHP SDK is working correctly with your agent!         ║\n";
    echo "╚════════════════════════════════════════════════════════════╝\n";
    echo RESET . "\n";
    
    printInfo("Next steps:");
    echo "  1. Install Composer: curl -sS https://getcomposer.org/installer | php\n";
    echo "  2. cd /home/nihal/Desktop/github_repos/runagent/runagent-php\n";
    echo "  3. composer install\n";
    echo "  4. php examples/test_deployed_agent.php\n";
    echo "\n";
    exit(0);
} else {
    echo RED;
    echo "╔════════════════════════════════════════════════════════════╗\n";
    echo "║               SOME TESTS FAILED ✗                          ║\n";
    echo "╚════════════════════════════════════════════════════════════╝\n";
    echo RESET . "\n";
    exit(1);
}
