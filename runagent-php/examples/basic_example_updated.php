<?php

/**
 * Basic example of using RunAgent PHP SDK
 * 
 * This example mirrors the Flutter SDK example and demonstrates:
 * - Creating a client for a deployed agent
 * - Running an agent with keyword arguments
 * - Error handling with suggestions
 */

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

// Create a client for your deployed agent
// Agent deployed in /home/nihal/Desktop/github_repos/runagent/nice/
$config = new RunAgentClientConfig(
    agentId: '91e70681-def8-4600-8a30-d037c1b51870',
    entrypointTag: 'agno_print_response',  // Non-streaming entrypoint
    local: true,                            // Running locally
    host: '0.0.0.0',                        // Agent host
    port: 8333,                             // Agent port
    apiKey: getenv('RUNAGENT_API_KEY') ?: 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6'
);

try {
    echo "Creating RunAgent client...\n";
    $client = RunAgentClient::create($config);
    echo "✓ Client created successfully\n\n";

    // Run the agent with input (similar to Flutter example)
    echo "Running agent with prompt...\n";
    $result = $client->run([
        'prompt' => 'Hello, world! Tell me a fun fact about PHP.',
    ]);

    echo "✓ Response received:\n";
    echo str_repeat('-', 60) . "\n";
    
    // Handle different response types
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

} catch (RunAgentError $e) {
    // Handle RunAgent-specific errors
    echo "Error: {$e->getMessage()}\n";
    
    if ($e->getSuggestion() !== null) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
    
    if ($e->getErrorCode() !== null) {
        echo "Error Code: {$e->getErrorCode()}\n";
    }
    
} catch (Exception $e) {
    // Handle unexpected errors
    echo "Unexpected error: {$e->getMessage()}\n";
}
