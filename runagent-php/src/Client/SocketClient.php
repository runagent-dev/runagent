<?php

namespace RunAgent\Client;

use RunAgent\Errors\AuthenticationError;
use RunAgent\Errors\ConnectionError;
use RunAgent\Errors\RunAgentExecutionError;
use RunAgent\Errors\ErrorCodes;
use RunAgent\Utils\Constants;
use Generator;

/**
 * WebSocket client for RunAgent streaming
 * 
 * Handles WebSocket connections for streaming agent execution.
 * Uses PHP streams for WebSocket communication.
 */
class SocketClient
{
    /**
     * @var string Base WebSocket URL
     */
    private string $baseSocketUrl;
    
    /**
     * @var string|null API key for authentication
     */
    private ?string $apiKey;
    
    /**
     * @var bool Whether this is a local agent
     */
    private bool $isLocal;

    /**
     * SocketClient constructor
     *
     * @param string $baseSocketUrl Base WebSocket URL
     * @param string|null $apiKey API key for authentication
     * @param bool $isLocal Whether this is a local agent
     */
    public function __construct(string $baseSocketUrl, ?string $apiKey = null, bool $isLocal = false)
    {
        $this->baseSocketUrl = $baseSocketUrl;
        $this->apiKey = $apiKey;
        $this->isLocal = $isLocal;
    }

    /**
     * Run agent with streaming
     *
     * @param string $agentId Agent ID
     * @param string $entrypointTag Entrypoint tag
     * @param array $inputArgs Positional arguments
     * @param array $inputKwargs Keyword arguments
     * @param int $timeoutSeconds Timeout in seconds
     * @return Generator Yields streamed chunks
     * @throws AuthenticationError
     * @throws ConnectionError
     * @throws RunAgentExecutionError
     */
    public function runStream(
        string $agentId,
        string $entrypointTag,
        array $inputArgs = [],
        array $inputKwargs = [],
        int $timeoutSeconds = 600
    ): Generator {
        // Build WebSocket URL
        $baseUri = $this->baseSocketUrl . Constants::DEFAULT_API_PREFIX . "/agents/{$agentId}/run-stream";
        
        if ($this->apiKey !== null) {
            // Add token to query string if API key is provided
            $uri = $baseUri . "?token={$this->apiKey}";
        } elseif (!$this->isLocal) {
            // Require API key for remote streaming
            throw new AuthenticationError(
                'api_key is required for remote streaming',
                'Set RUNAGENT_API_KEY or pass apiKey parameter'
            );
        } else {
            $uri = $baseUri;
        }

        // Ensure proper WebSocket protocol
        $wsUri = $this->normalizeWebSocketUri($uri);

        // Parse URL for connection
        $parsed = parse_url($wsUri);
        if ($parsed === false) {
            throw new ConnectionError('Invalid WebSocket URL');
        }

        $scheme = $parsed['scheme'] ?? 'ws';
        $host = $parsed['host'] ?? 'localhost';
        $port = $parsed['port'] ?? ($scheme === 'wss' ? 443 : 80);
        $path = ($parsed['path'] ?? '/') . (isset($parsed['query']) ? '?' . $parsed['query'] : '');

        // Connect via stream socket
        $socket = $this->connect($scheme, $host, $port, $path);

        try {
            // Send initial request
            $requestData = [
                'entrypoint_tag' => $entrypointTag,
                'input_args' => $inputArgs,
                'input_kwargs' => $inputKwargs,
                'timeout_seconds' => $timeoutSeconds,
            ];

            $this->sendMessage($socket, json_encode($requestData));

            // Stream responses
            while (!feof($socket)) {
                $message = $this->receiveMessage($socket);
                
                if ($message === null) {
                    continue;
                }

                try {
                    $json = json_decode($message, true);
                    if ($json === null) {
                        yield $message;
                        continue;
                    }

                    $type = $json['type'] ?? null;

                    if ($type === 'error') {
                        $errorData = $json['data'] ?? $json['error'] ?? [];
                        $errorMessage = is_array($errorData) ? ($errorData['message'] ?? 'Stream error') : (is_string($errorData) ? $errorData : 'Stream error');
                        $errorCode = is_array($errorData) ? ($errorData['code'] ?? ErrorCodes::SERVER_ERROR) : ErrorCodes::SERVER_ERROR;
                        $suggestion = is_array($errorData) ? ($errorData['suggestion'] ?? null) : null;

                        throw new RunAgentExecutionError(
                            $errorCode,
                            $errorMessage,
                            $suggestion
                        );
                    } elseif ($type === 'status') {
                        $status = $json['status'] ?? null;
                        if ($status === 'stream_completed') {
                            break;
                        }
                        // Continue for other status messages
                    } elseif ($type === 'data') {
                        $data = $json['data'] ?? $json['content'] ?? null;
                        if ($data !== null) {
                            yield $this->deserializeChunk($data);
                        }
                    } else {
                        yield $json;
                    }
                } catch (RunAgentExecutionError $e) {
                    throw $e;
                } catch (\Exception) {
                    yield $message;
                }
            }
        } finally {
            fclose($socket);
        }
    }

    /**
     * Normalize WebSocket URI
     *
     * @param string $uri Original URI
     * @return string Normalized WebSocket URI
     */
    private function normalizeWebSocketUri(string $uri): string
    {
        if (str_starts_with($uri, 'ws://') || str_starts_with($uri, 'wss://')) {
            return $uri;
        }
        
        if (str_starts_with($uri, 'http://')) {
            return str_replace('http://', 'ws://', $uri);
        }
        
        if (str_starts_with($uri, 'https://')) {
            return str_replace('https://', 'wss://', $uri);
        }
        
        return 'wss://' . $uri;
    }

    /**
     * Connect to WebSocket server
     *
     * @param string $scheme ws or wss
     * @param string $host Host
     * @param int $port Port
     * @param string $path Path
     * @return resource Socket resource
     * @throws ConnectionError
     */
    private function connect(string $scheme, string $host, int $port, string $path)
    {
        $address = ($scheme === 'wss' ? 'ssl://' : '') . $host . ':' . $port;
        
        $errno = 0;
        $errstr = '';
        $socket = @stream_socket_client(
            $address,
            $errno,
            $errstr,
            10,
            STREAM_CLIENT_CONNECT
        );

        if ($socket === false) {
            throw new ConnectionError(
                "Failed to open WebSocket connection: {$errstr} ({$errno})",
                'Check your network connection or agent status'
            );
        }

        // Send WebSocket handshake
        $key = base64_encode(random_bytes(16));
        $handshake = "GET {$path} HTTP/1.1\r\n";
        $handshake .= "Host: {$host}:{$port}\r\n";
        $handshake .= "Upgrade: websocket\r\n";
        $handshake .= "Connection: Upgrade\r\n";
        $handshake .= "Sec-WebSocket-Key: {$key}\r\n";
        $handshake .= "Sec-WebSocket-Version: 13\r\n";
        $handshake .= "User-Agent: " . Constants::userAgent() . "\r\n";
        $handshake .= "\r\n";

        fwrite($socket, $handshake);

        // Read handshake response
        $response = '';
        while (!feof($socket) && strpos($response, "\r\n\r\n") === false) {
            $response .= fgets($socket, 1024);
        }

        if (strpos($response, '101 Switching Protocols') === false) {
            fclose($socket);
            throw new ConnectionError('WebSocket handshake failed');
        }

        return $socket;
    }

    /**
     * Send WebSocket message
     *
     * @param resource $socket Socket resource
     * @param string $message Message to send
     */
    private function sendMessage($socket, string $message): void
    {
        $length = strlen($message);
        $frame = chr(0x81); // Text frame, FIN bit set

        if ($length <= 125) {
            $frame .= chr($length | 0x80); // Mask bit set
        } elseif ($length <= 65535) {
            $frame .= chr(126 | 0x80);
            $frame .= pack('n', $length);
        } else {
            $frame .= chr(127 | 0x80);
            $frame .= pack('J', $length);
        }

        // Generate masking key
        $mask = random_bytes(4);
        $frame .= $mask;

        // Mask the payload
        for ($i = 0; $i < $length; $i++) {
            $frame .= $message[$i] ^ $mask[$i % 4];
        }

        fwrite($socket, $frame);
    }

    /**
     * Receive WebSocket message
     *
     * @param resource $socket Socket resource
     * @return string|null Received message or null
     */
    private function receiveMessage($socket): ?string
    {
        $header = fread($socket, 2);
        if ($header === false || strlen($header) < 2) {
            return null;
        }

        $byte1 = ord($header[0]);
        $byte2 = ord($header[1]);

        $opcode = $byte1 & 0x0F;
        $masked = ($byte2 & 0x80) !== 0;
        $payloadLength = $byte2 & 0x7F;

        // Connection close
        if ($opcode === 0x08) {
            return null;
        }

        // Continuation or text frame
        if ($opcode !== 0x00 && $opcode !== 0x01) {
            return null;
        }

        if ($payloadLength === 126) {
            $extended = fread($socket, 2);
            $payloadLength = unpack('n', $extended)[1];
        } elseif ($payloadLength === 127) {
            $extended = fread($socket, 8);
            $payloadLength = unpack('J', $extended)[1];
        }

        $maskingKey = $masked ? fread($socket, 4) : null;
        $payload = fread($socket, $payloadLength);

        if ($masked && $maskingKey !== null) {
            for ($i = 0; $i < $payloadLength; $i++) {
                $payload[$i] = $payload[$i] ^ $maskingKey[$i % 4];
            }
        }

        return $payload;
    }

    /**
     * Deserialize chunk data (handles structured format {type, payload})
     *
     * @param mixed $data Chunk data
     * @return mixed Deserialized data
     */
    private function deserializeChunk($data)
    {
        // If data is a string, try to parse as JSON
        if (is_string($data)) {
            $parsed = json_decode($data, true);
            if ($parsed !== null) {
                return $this->deserializeStructured($parsed);
            }
            return $data;
        }
        
        // If data is already an array, check for structured format
        if (is_array($data)) {
            return $this->deserializeStructured($data);
        }
        
        return $data;
    }

    /**
     * Deserialize structured format {type, payload}
     *
     * @param mixed $data Data to deserialize
     * @return mixed Deserialized data
     */
    private function deserializeStructured($data)
    {
        if (!is_array($data)) {
            return $data;
        }
        
        // Check for structured format {type, payload}
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
