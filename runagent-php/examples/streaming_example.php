<?php

require_once __DIR__ . '/../vendor/autoload.php';

use RunAgent\Client\RunAgentClient;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Errors\RunAgentError;

/**
 * Streaming example
 * 
 * This example demonstrates:
 * - Creating a client with a streaming entrypoint
 * - Using runStream() to get streaming responses
 * - Processing streamed chunks
 */

try {
    // Create a client for a streaming entrypoint
    // Note: entrypoint tag must end with '_stream'
    $config = new RunAgentClientConfig(
        agentId: 'YOUR_AGENT_ID',
        entrypointTag: 'chat_stream',  // Must end with '_stream'
        apiKey: getenv('RUNAGENT_API_KEY')
    );
    
    $client = RunAgentClient::create($config);

    echo "Streaming response:\n";
    echo "-------------------\n";

    // Stream responses
    foreach ($client->runStream([
        'prompt' => 'Write a haiku about PHP',
    ]) as $chunk) {
        // Each chunk is yielded as it arrives
        if (is_string($chunk)) {
            echo $chunk;
        } else {
            echo print_r($chunk, true);
        }
        flush();
    }

    echo "\n-------------------\n";
    echo "Stream completed\n";
    
} catch (RunAgentError $e) {
    echo "Error [{$e->getErrorCode()}]: {$e->getMessage()}\n";
    if ($e->getSuggestion() !== null) {
        echo "Suggestion: {$e->getSuggestion()}\n";
    }
} catch (Exception $e) {
    echo "Unexpected error: {$e->getMessage()}\n";
}
