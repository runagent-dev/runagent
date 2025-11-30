<?php

namespace RunAgent\Client;

use RunAgent\Errors\AuthenticationError;
use RunAgent\Errors\ConnectionError;
use RunAgent\Errors\ServerError;
use RunAgent\Errors\ValidationError;
use RunAgent\Errors\RunAgentError;
use RunAgent\Utils\Constants;

/**
 * REST client for RunAgent API
 * 
 * Handles HTTP requests for non-streaming agent execution.
 */
class RestClient
{
    /**
     * @var string Base URL for REST API
     */
    private string $baseUrl;
    
    /**
     * @var string|null API key for authentication
     */
    private ?string $apiKey;
    
    /**
     * @var bool Whether this is a local agent
     */
    private bool $isLocal;

    /**
     * RestClient constructor
     *
     * @param string $baseUrl Base URL for REST API
     * @param string|null $apiKey API key for authentication
     * @param bool $isLocal Whether this is a local agent
     */
    public function __construct(string $baseUrl, ?string $apiKey = null, bool $isLocal = false)
    {
        $this->baseUrl = $baseUrl;
        $this->apiKey = $apiKey;
        $this->isLocal = $isLocal;
    }

    /**
     * Get agent architecture
     *
     * @param string $agentId Agent ID
     * @return array Agent architecture data
     * @throws RunAgentError
     */
    public function getAgentArchitecture(string $agentId): array
    {
        $url = $this->baseUrl . Constants::DEFAULT_API_PREFIX . "/agents/{$agentId}/architecture";
        
        $headers = [
            'Content-Type: application/json',
            'User-Agent: ' . Constants::userAgent(),
        ];

        // Send API key if available (for both local and remote)
        if ($this->apiKey !== null) {
            $headers[] = 'Authorization: Bearer ' . $this->apiKey;
        }

        $response = $this->makeRequest('GET', $url, $headers);
        return $response;
    }

    /**
     * Run agent via REST
     *
     * @param string $agentId Agent ID
     * @param string $entrypointTag Entrypoint tag
     * @param array $inputArgs Positional arguments
     * @param array $inputKwargs Keyword arguments
     * @param int $timeoutSeconds Timeout in seconds
     * @param bool $asyncExecution Whether to execute asynchronously
     * @return array Response data
     * @throws RunAgentError
     */
    public function runAgent(
        string $agentId,
        string $entrypointTag,
        array $inputArgs = [],
        array $inputKwargs = [],
        int $timeoutSeconds = 300,
        bool $asyncExecution = false
    ): array {
        $url = $this->baseUrl . Constants::DEFAULT_API_PREFIX . "/agents/{$agentId}/run";
        
        $headers = [
            'Content-Type: application/json',
            'User-Agent: ' . Constants::userAgent(),
        ];

        // Send API key if available (for both local and remote)
        if ($this->apiKey !== null) {
            $headers[] = 'Authorization: Bearer ' . $this->apiKey;
        } elseif (!$this->isLocal) {
            // Only throw error for remote if no API key
            throw new AuthenticationError(
                'api_key is required for remote runs',
                'Set RUNAGENT_API_KEY or pass apiKey parameter'
            );
        }

        $payload = [
            'entrypoint_tag' => $entrypointTag,
            'input_args' => $inputArgs,
            'input_kwargs' => $inputKwargs,
            'timeout_seconds' => $timeoutSeconds,
            'async_execution' => $asyncExecution,
        ];

        $response = $this->makeRequest('POST', $url, $headers, $payload, $timeoutSeconds + 10);
        return $response;
    }

    /**
     * Health check
     *
     * @return bool True if healthy
     */
    public function healthCheck(): bool
    {
        try {
            $url = $this->baseUrl . Constants::DEFAULT_API_PREFIX . '/health';
            $this->makeRequest('GET', $url, []);
            return true;
        } catch (\Exception) {
            return false;
        }
    }

    /**
     * Make HTTP request
     *
     * @param string $method HTTP method
     * @param string $url URL
     * @param array $headers Headers
     * @param array|null $payload Request payload
     * @param int $timeout Timeout in seconds
     * @return array Response data
     * @throws RunAgentError
     */
    private function makeRequest(
        string $method,
        string $url,
        array $headers,
        ?array $payload = null,
        int $timeout = 30
    ): array {
        $ch = curl_init();
        
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
        
        if ($method === 'POST') {
            curl_setopt($ch, CURLOPT_POST, true);
            if ($payload !== null) {
                curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
            }
        } elseif ($method === 'GET') {
            curl_setopt($ch, CURLOPT_HTTPGET, true);
        }

        $response = curl_exec($ch);
        $statusCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($response === false) {
            throw new ConnectionError(
                "Failed to reach RunAgent service: {$error}",
                'Check your network connection or agent status'
            );
        }

        if ($statusCode !== 200) {
            throw $this->translateHttpError($statusCode, $response);
        }

        $data = json_decode($response, true);
        if ($data === null) {
            throw new ServerError('Invalid JSON response from server');
        }

        return $data;
    }

    /**
     * Translate HTTP error to RunAgent error
     *
     * @param int $statusCode HTTP status code
     * @param string $body Response body
     * @return RunAgentError
     */
    private function translateHttpError(int $statusCode, string $body): RunAgentError
    {
        $errorPayload = null;
        
        try {
            $json = json_decode($body, true);
            if ($json !== null && isset($json['error'])) {
                $errorPayload = $this->parseApiError($json['error']);
            }
        } catch (\Exception) {
            // Ignore JSON parse errors
        }

        $error = $errorPayload ?? [
            'type' => 'SERVER_ERROR',
            'message' => "Server returned status {$statusCode}",
        ];

        $errorMessage = $error['message'] ?? 'Unknown error';
        $errorSuggestion = $error['suggestion'] ?? null;
        $errorDetails = $error['details'] ?? null;
        
        if ($statusCode === 401 || $statusCode === 403) {
            return new AuthenticationError(
                $errorMessage,
                $errorSuggestion ?? 'Set RUNAGENT_API_KEY or pass apiKey parameter',
                $errorDetails
            );
        } elseif ($statusCode >= 500) {
            return new ServerError($errorMessage, $errorSuggestion, $errorDetails);
        } else {
            return new ValidationError($errorMessage, $errorSuggestion, $errorDetails);
        }
    }

    /**
     * Parse API error from response
     *
     * @param mixed $rawError Raw error data
     * @return array|null Parsed error
     */
    private function parseApiError($rawError): ?array
    {
        if ($rawError === null) {
            return null;
        }
        
        if (is_string($rawError)) {
            return [
                'type' => 'SERVER_ERROR',
                'message' => $rawError,
            ];
        }
        
        if (is_array($rawError)) {
            return [
                'type' => $rawError['type'] ?? 'SERVER_ERROR',
                'message' => $rawError['message'] ?? 'Unknown error',
                'code' => $rawError['code'] ?? null,
                'suggestion' => $rawError['suggestion'] ?? null,
                'details' => $rawError['details'] ?? null,
            ];
        }
        
        return null;
    }
}
