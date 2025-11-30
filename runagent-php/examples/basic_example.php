<?php

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

/**
 * Basic example of using RunAgent PHP SDK
 * 
 * This example demonstrates:
 * - Creating a remote client
 * - Running an agent with keyword arguments
 * - Error handling
 */

try {
    // Create a client for a remote agent
    $config = new RunAgentClientConfig(
        agentId: 'YOUR_AGENT_ID',
        entrypointTag: 'generic',
        apiKey: getenv('RUNAGENT_API_KEY')
    );
    
    $client = RunAgentClient::create($config);

    // Run the agent with input
    $result = $client->run([
        'message' => 'Hello, world!',
        'temperature' => 0.7,
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
