<?php

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

/**
 * Local agent example
 * 
 * This example demonstrates:
 * - Creating a local client
 * - Connecting to a locally running agent
 * - Running with explicit host/port
 */

try {
    // Create a client for a local agent
    // Note: The agent must be running locally first
    $config = new RunAgentClientConfig(
        agentId: 'local-agent-id',
        entrypointTag: 'generic',
        local: true,
        host: '127.0.0.1',  // Optional: falls back to DB entry
        port: 8450
    );
    
    $client = RunAgentClient::create($config);

    // Check if agent is healthy
    if ($client->healthCheck()) {
        echo "Agent is healthy!\n";
    } else {
        echo "Agent health check failed\n";
        exit(1);
    }

    // Run the agent
    $result = $client->run([
        'prompt' => 'What is the meaning of life?',
    ]);

    echo "Response: " . print_r($result, true) . "\n";
    
} catch (RunAgentError $e) {
    echo "Error [{$e->getErrorCode()}]: {$e->getMessage()}\n";
    if ($e->getSuggestion() !== null) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
} catch (Exception $e) {
    echo "Unexpected error: {$e->getMessage()}\n";
}
