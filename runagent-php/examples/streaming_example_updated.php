<?php

/**
 * Streaming example of using RunAgent PHP SDK
 * 
 * This example demonstrates:
 * - Creating a client for a streaming entrypoint
 * - Receiving and displaying streaming chunks
 * - Error handling
 */

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

// Create a client for your deployed agent's streaming entrypoint
// Agent deployed in /home/nihal/Desktop/github_repos/runagent/nice/
$config = new RunAgentClientConfig(
    agentId: '91e70681-def8-4600-8a30-d037c1b51870',
    entrypointTag: 'agno_print_response_stream',  // Streaming entrypoint
    local: true,
    host: '0.0.0.0',
    port: 8333,
    apiKey: getenv('RUNAGENT_API_KEY') ?: 'rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6'
);

try {
    echo "Creating RunAgent streaming client...\n";
    $client = RunAgentClient::create($config);
    echo "✓ Client created successfully\n\n";

    // Run the agent with streaming
    echo "Streaming agent response:\n";
    echo str_repeat('-', 60) . "\n";
    
    $chunkCount = 0;
    foreach ($client->runStream(['prompt' => 'Write a short haiku about coding in PHP.']) as $chunk) {
        $chunkCount++;
        
        // Handle different chunk formats
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
        
        flush(); // Ensure immediate output
    }
    
    echo "\n" . str_repeat('-', 60) . "\n";
    echo "✓ Received $chunkCount chunks\n";

} catch (RunAgentError $e) {
    echo "Error: {$e->getMessage()}\n";
    
    if ($e->getSuggestion() !== null) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
    
} catch (Exception $e) {
    echo "Unexpected error: {$e->getMessage()}\n";
}
