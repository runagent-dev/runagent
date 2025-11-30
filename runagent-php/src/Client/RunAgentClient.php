<?php

namespace RunAgent\Client;

use RunAgent\Errors\RunAgentExecutionError;
use RunAgent\Errors\ServerError;
use RunAgent\Errors\ValidationError;
use RunAgent\Errors\ErrorCodes;
use RunAgent\Types\RunAgentClientConfig;
use RunAgent\Types\AgentArchitecture;
use RunAgent\Utils\ConfigUtils;
use RunAgent\Utils\Constants;
use Generator;

/**
 * Main client for interacting with RunAgent deployments
 * 
 * Follows SDK checklist requirements for client initialization, 
 * configuration precedence, and error handling.
 */
class RunAgentClient
{
    /**
     * @var string Agent ID
     */
    private string $agentId;
    
    /**
     * @var string Entrypoint tag
     */
    private string $entrypointTag;
    
    /**
     * @var bool Whether this is a local agent
     */
    private bool $local;
    
    /**
     * @var RestClient REST client for non-streaming requests
     */
    private RestClient $restClient;
    
    /**
     * @var SocketClient Socket client for streaming requests
     */
    private SocketClient $socketClient;
    
    /**
     * @var array|null Extra parameters for future use
     */
    private ?array $extraParams;
    
    /**
     * @var AgentArchitecture|null Cached architecture
     */
    private ?AgentArchitecture $architecture = null;

    /**
     * RunAgentClient constructor (private - use create() factory method)
     *
     * @param string $agentId Agent ID
     * @param string $entrypointTag Entrypoint tag
     * @param bool $local Whether this is a local agent
     * @param RestClient $restClient REST client
     * @param SocketClient $socketClient Socket client
     * @param array|null $extraParams Extra parameters
     */
    private function __construct(
        string $agentId,
        string $entrypointTag,
        bool $local,
        RestClient $restClient,
        SocketClient $socketClient,
        ?array $extraParams = null
    ) {
        $this->agentId = $agentId;
        $this->entrypointTag = $entrypointTag;
        $this->local = $local;
        $this->restClient = $restClient;
        $this->socketClient = $socketClient;
        $this->extraParams = $extraParams;
    }

    /**
     * Create a new RunAgent client from configuration
     *
     * @param RunAgentClientConfig $config Client configuration
     * @return self
     * @throws ValidationError
     * @throws RunAgentExecutionError
     */
    public static function create(RunAgentClientConfig $config): self
    {
        // Validate required fields
        if (trim($config->agentId) === '') {
            throw new ValidationError('agent_id is required');
        }
        if (trim($config->entrypointTag) === '') {
            throw new ValidationError('entrypoint_tag is required');
        }

        // Resolve configuration with precedence: explicit > env > default
        $local = ConfigUtils::resolveBool(
            $config->local,
            ConfigUtils::getLocal(),
            false
        );

        $enableRegistry = $config->enableRegistry ?? $local;

        // Resolve host/port for local agents
        $host = null;
        $port = null;

        if ($local) {
            $host = ConfigUtils::firstNonEmpty([
                $config->host,
                ConfigUtils::getHost(),
            ]);
            $port = ConfigUtils::firstNonZero([
                $config->port,
                ConfigUtils::getPort(),
            ]);

            // Try database lookup if enabled and host/port not provided
            if ($enableRegistry && ($host === null || $port === null)) {
                // TODO: Implement database lookup for PHP
                // For now, use defaults or require explicit host/port
                if ($host === null) {
                    $host = Constants::DEFAULT_LOCAL_HOST;
                }
                if ($port === null) {
                    $port = Constants::DEFAULT_LOCAL_PORT;
                }
            }

            if ($host === null || $port === null) {
                throw new ValidationError(
                    'Host and port are required for local agents',
                    'Pass host/port in config or enable registry for database lookup'
                );
            }
        }

        // Resolve API key (config > env var)
        $apiKey = ConfigUtils::firstNonEmpty([
            $config->apiKey,
            ConfigUtils::getApiKey(),
        ]);

        // Resolve base URL (config > env var > default)
        $baseUrl = ConfigUtils::firstNonEmpty([
            $config->baseUrl,
            ConfigUtils::getBaseUrl(),
        ]) ?? Constants::DEFAULT_BASE_URL;

        // Create REST and WebSocket clients
        [$restClient, $socketClient] = $local
            ? self::createLocalClients($host, $port, $apiKey)
            : self::createRemoteClients($baseUrl, $apiKey);

        $client = new self(
            $config->agentId,
            $config->entrypointTag,
            $local,
            $restClient,
            $socketClient,
            $config->extraParams
        );

        // Initialize architecture and validate entrypoint
        $client->initializeArchitecture();

        return $client;
    }

    /**
     * Create local clients
     *
     * @param string $host Host
     * @param int $port Port
     * @param string|null $apiKey API key
     * @return array [RestClient, SocketClient]
     */
    private static function createLocalClients(string $host, int $port, ?string $apiKey): array
    {
        $restBase = "http://{$host}:{$port}";
        $socketBase = "ws://{$host}:{$port}";

        $restClient = new RestClient($restBase, $apiKey, true);
        $socketClient = new SocketClient($socketBase, $apiKey, true);

        return [$restClient, $socketClient];
    }

    /**
     * Create remote clients
     *
     * @param string $baseUrl Base URL
     * @param string|null $apiKey API key
     * @return array [RestClient, SocketClient]
     */
    private static function createRemoteClients(string $baseUrl, ?string $apiKey): array
    {
        // Normalize base URL
        $normalizedBase = trim($baseUrl);
        if (!str_starts_with($normalizedBase, 'http://') && !str_starts_with($normalizedBase, 'https://')) {
            $normalizedBase = 'https://' . $normalizedBase;
        }
        $normalizedBase = rtrim($normalizedBase, '/');

        // Convert to WebSocket URL
        $socketBase = str_replace(['https://', 'http://'], ['wss://', 'ws://'], $normalizedBase);

        $restClient = new RestClient($normalizedBase, $apiKey, false);
        $socketClient = new SocketClient($socketBase, $apiKey, false);

        return [$restClient, $socketClient];
    }

    /**
     * Initialize architecture and validate entrypoint
     *
     * @throws ValidationError
     * @throws RunAgentExecutionError
     * @throws ServerError
     */
    private function initializeArchitecture(): void
    {
        $architectureJson = $this->restClient->getAgentArchitecture($this->agentId);
        
        // Handle envelope format
        if (isset($architectureJson['success'])) {
            $success = $architectureJson['success'];
            if ($success === false) {
                $error = $architectureJson['error'] ?? [];
                if (is_array($error)) {
                    $errorMessage = $error['message'] ?? 'Failed to retrieve agent architecture';
                    $errorCode = $error['code'] ?? ErrorCodes::SERVER_ERROR;
                    throw new RunAgentExecutionError(
                        $errorCode,
                        $errorMessage,
                        $error['suggestion'] ?? null,
                        $error['details'] ?? null
                    );
                }
                $message = $architectureJson['message'] ?? 'Failed to retrieve agent architecture';
                throw new ServerError($message);
            }
            
            $data = $architectureJson['data'] ?? null;
            if ($data !== null) {
                $this->architecture = AgentArchitecture::fromArray($data);
            }
        } else {
            // Legacy format
            $this->architecture = AgentArchitecture::fromArray($architectureJson);
        }

        // Validate entrypoint exists
        if ($this->architecture === null || empty($this->architecture->entrypoints)) {
            throw new ValidationError(
                'Architecture missing entrypoints',
                'Redeploy the agent with entrypoints configured'
            );
        }

        $found = false;
        foreach ($this->architecture->entrypoints as $ep) {
            if ($ep->tag === $this->entrypointTag) {
                $found = true;
                break;
            }
        }

        if (!$found) {
            $available = array_map(fn($ep) => $ep->tag, $this->architecture->entrypoints);
            throw new ValidationError(
                "Entrypoint `{$this->entrypointTag}` not found in agent {$this->agentId}",
                'Available entrypoints: ' . implode(', ', $available)
            );
        }
    }

    /**
     * Run the agent with keyword arguments
     *
     * @param array $inputKwargs Keyword arguments (associative array)
     * @return mixed Agent response
     * @throws ValidationError
     * @throws RunAgentExecutionError
     */
    public function run(array $inputKwargs = [])
    {
        return $this->runWithArgs([], $inputKwargs);
    }

    /**
     * Run the agent with both positional and keyword arguments
     *
     * @param array $inputArgs Positional arguments (indexed array)
     * @param array $inputKwargs Keyword arguments (associative array)
     * @return mixed Agent response
     * @throws ValidationError
     * @throws RunAgentExecutionError
     */
    public function runWithArgs(array $inputArgs = [], array $inputKwargs = [])
    {
        // Guardrail: non-stream only
        if (str_ends_with(strtolower($this->entrypointTag), '_stream')) {
            throw new ValidationError(
                'Stream entrypoint must be invoked with runStream',
                'Use client->runStream(...) for *_stream tags'
            );
        }

        $response = $this->restClient->runAgent(
            $this->agentId,
            $this->entrypointTag,
            $inputArgs,
            $inputKwargs
        );

        if (($response['success'] ?? false) === true) {
            // Process response data
            $payload = null;

            $data = $response['data'] ?? null;
            if (is_string($data)) {
                // Case 1: data is a string (could be structured JSON string with {type, payload})
                $payload = $this->deserializeString($data);
            } elseif (is_array($data)) {
                // Case 2: data has result_data.data (legacy detailed execution payload)
                if (isset($data['result_data'])) {
                    $resultData = $data['result_data'];
                    $innerData = $resultData['data'] ?? null;
                    // Check if innerData is a string that needs deserialization
                    if (is_string($innerData)) {
                        $payload = $this->deserializeString($innerData);
                    } else {
                        $payload = $this->deserializeObject($innerData);
                    }
                } else {
                    // Case 3: data is an object (could be {type, payload} structure)
                    $payload = $this->deserializeObject($data);
                }
            } elseif ($data !== null) {
                $payload = $this->deserializeObject($data);
            } elseif (isset($response['output_data'])) {
                // Case 4: Fallback to output_data (backward compatibility)
                $outputData = $response['output_data'];
                if (is_string($outputData)) {
                    $payload = $this->deserializeString($outputData);
                } else {
                    $payload = $this->deserializeObject($outputData);
                }
            }

            // Check for generator object warning
            if (is_string($payload)) {
                $lowerStr = strtolower($payload);
                if (str_contains($lowerStr, 'generator object') || str_contains($lowerStr, '<generator')) {
                    $streamingTag = $this->entrypointTag . '_stream';
                    throw new ValidationError(
                        'Agent returned a generator object instead of content. This entrypoint appears to be a streaming function.',
                        "Try using the streaming endpoint: `{$streamingTag}`\nOr use runStream() method instead of run()."
                    );
                }
            }

            return $payload;
        } else {
            // Handle error format
            $error = $response['error'] ?? null;
            if (is_array($error)) {
                throw new RunAgentExecutionError(
                    $error['code'] ?? ErrorCodes::SERVER_ERROR,
                    $error['message'] ?? 'Unknown error',
                    $error['suggestion'] ?? null,
                    $error['details'] ?? null
                );
            } elseif (is_string($error)) {
                throw new RunAgentExecutionError(
                    ErrorCodes::SERVER_ERROR,
                    $error
                );
            } else {
                throw new RunAgentExecutionError(
                    ErrorCodes::SERVER_ERROR,
                    'Unknown error'
                );
            }
        }
    }

    /**
     * Run the agent and return a stream of responses
     *
     * @param array $inputKwargs Keyword arguments (associative array)
     * @return Generator Yields streamed chunks
     * @throws ValidationError
     */
    public function runStream(array $inputKwargs = []): Generator
    {
        return $this->runStreamWithArgs([], $inputKwargs);
    }

    /**
     * Run the agent with streaming and both positional and keyword arguments
     *
     * @param array $inputArgs Positional arguments (indexed array)
     * @param array $inputKwargs Keyword arguments (associative array)
     * @return Generator Yields streamed chunks
     * @throws ValidationError
     */
    public function runStreamWithArgs(array $inputArgs = [], array $inputKwargs = []): Generator
    {
        // Guardrail: stream only
        if (!str_ends_with(strtolower($this->entrypointTag), '_stream')) {
            throw new ValidationError(
                'Non-stream entrypoint must be invoked with run',
                'Use client->run(...) for non-stream tags'
            );
        }

        return $this->socketClient->runStream(
            $this->agentId,
            $this->entrypointTag,
            $inputArgs,
            $inputKwargs
        );
    }

    /**
     * Get the agent's architecture information
     *
     * @return AgentArchitecture
     * @throws ValidationError
     * @throws RunAgentExecutionError
     * @throws ServerError
     */
    public function getAgentArchitecture(): AgentArchitecture
    {
        if ($this->architecture !== null) {
            return $this->architecture;
        }

        $this->initializeArchitecture();
        
        if ($this->architecture === null) {
            throw new ValidationError('Failed to initialize architecture');
        }
        
        return $this->architecture;
    }

    /**
     * Check if the agent is available
     *
     * @return bool True if healthy
     */
    public function healthCheck(): bool
    {
        return $this->restClient->healthCheck();
    }

    /**
     * Get agent ID
     *
     * @return string
     */
    public function getAgentId(): string
    {
        return $this->agentId;
    }

    /**
     * Get entrypoint tag
     *
     * @return string
     */
    public function getEntrypointTag(): string
    {
        return $this->entrypointTag;
    }

    /**
     * Get any extra params supplied during initialization
     *
     * @return array|null
     */
    public function getExtraParams(): ?array
    {
        return $this->extraParams;
    }

    /**
     * Check if using local deployment
     *
     * @return bool
     */
    public function isLocal(): bool
    {
        return $this->local;
    }

    /**
     * Deserialize string payload
     *
     * @param string $data String data
     * @return mixed Deserialized data
     */
    private function deserializeString(string $data)
    {
        // Try to parse as JSON
        $parsed = json_decode($data, true);
        
        // If it's a structured format {type, payload}, deserialize it
        if (is_array($parsed)) {
            return $this->deserializeObject($parsed);
        }
        
        return $parsed ?? $data;
    }

    /**
     * Deserialize object payload
     *
     * @param mixed $data Object data
     * @return mixed Deserialized data
     */
    private function deserializeObject($data)
    {
        // Handle null
        if ($data === null) {
            return null;
        }
        
        // If it's not an array, return as-is
        if (!is_array($data)) {
            return $data;
        }
        
        // Check for structured object with payload field (matching Python SDK)
        if (isset($data['type']) && isset($data['payload'])) {
            $type = $data['type'];
            $payload = $data['payload'];
            
            // Parse payload based on type (matching Python serializer logic)
            switch ($type) {
                case 'null':
                    return null;
                case 'string':
                case 'integer':
                case 'number':
                case 'boolean':
                case 'array':
                case 'object':
                    return json_decode($payload, true) ?? $payload;
                default:
                    return json_decode($payload, true) ?? $payload;
            }
        }
        
        return $data;
    }
}
