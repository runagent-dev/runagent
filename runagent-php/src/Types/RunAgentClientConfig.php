<?php

namespace RunAgent\Types;

/**
 * Configuration for RunAgentClient
 * 
 * Follows the SDK checklist requirements for client initialization contract.
 */
class RunAgentClientConfig
{
    /**
     * @var string Agent ID (required)
     */
    public string $agentId;
    
    /**
     * @var string Entrypoint tag (required)
     */
    public string $entrypointTag;
    
    /**
     * @var bool|null Whether this is a local agent (default: false)
     */
    public ?bool $local;
    
    /**
     * @var string|null Host for local agents (optional, will lookup from DB if not provided and local=true)
     */
    public ?string $host;
    
    /**
     * @var int|null Port for local agents (optional, will lookup from DB if not provided and local=true)
     */
    public ?int $port;
    
    /**
     * @var string|null API key for remote agents (optional, can also use RUNAGENT_API_KEY env var)
     */
    public ?string $apiKey;
    
    /**
     * @var string|null Base URL for remote agents (optional, defaults to https://backend.run-agent.ai)
     */
    public ?string $baseUrl;
    
    /**
     * @var array|null Extra parameters for future use
     */
    public ?array $extraParams;
    
    /**
     * @var bool|null Enable database registry lookup (default: true for local agents)
     */
    public ?bool $enableRegistry;

    /**
     * RunAgentClientConfig constructor
     *
     * @param string $agentId Agent ID (required)
     * @param string $entrypointTag Entrypoint tag (required)
     * @param bool|null $local Whether this is a local agent
     * @param string|null $host Host for local agents
     * @param int|null $port Port for local agents
     * @param string|null $apiKey API key for remote agents
     * @param string|null $baseUrl Base URL for remote agents
     * @param array|null $extraParams Extra parameters for future use
     * @param bool|null $enableRegistry Enable database registry lookup
     */
    public function __construct(
        string $agentId,
        string $entrypointTag,
        ?bool $local = null,
        ?string $host = null,
        ?int $port = null,
        ?string $apiKey = null,
        ?string $baseUrl = null,
        ?array $extraParams = null,
        ?bool $enableRegistry = null
    ) {
        $this->agentId = $agentId;
        $this->entrypointTag = $entrypointTag;
        $this->local = $local;
        $this->host = $host;
        $this->port = $port;
        $this->apiKey = $apiKey;
        $this->baseUrl = $baseUrl;
        $this->extraParams = $extraParams;
        $this->enableRegistry = $enableRegistry;
    }
}

/**
 * Agent architecture information
 */
class AgentArchitecture
{
    /**
     * @var string Agent ID
     */
    public string $agentId;
    
    /**
     * @var EntryPoint[] Array of entrypoints
     */
    public array $entrypoints;

    /**
     * AgentArchitecture constructor
     *
     * @param string $agentId Agent ID
     * @param EntryPoint[] $entrypoints Array of entrypoints
     */
    public function __construct(string $agentId, array $entrypoints)
    {
        $this->agentId = $agentId;
        $this->entrypoints = $entrypoints;
    }

    /**
     * Create from JSON data
     *
     * @param array $data JSON data
     * @return self
     */
    public static function fromArray(array $data): self
    {
        $agentId = $data['agent_id'] ?? $data['agentId'] ?? '';
        $entrypointsData = $data['entrypoints'] ?? [];
        
        $entrypoints = [];
        foreach ($entrypointsData as $epData) {
            if (is_array($epData)) {
                $entrypoints[] = EntryPoint::fromArray($epData);
            }
        }
        
        return new self($agentId, $entrypoints);
    }
}

/**
 * Entry point definition
 */
class EntryPoint
{
    /**
     * @var string Entrypoint tag
     */
    public string $tag;
    
    /**
     * @var string|null File path
     */
    public ?string $file;
    
    /**
     * @var string|null Module name
     */
    public ?string $module;
    
    /**
     * @var string|null Extractor function
     */
    public ?string $extractor;
    
    /**
     * @var string|null Description
     */
    public ?string $description;

    /**
     * EntryPoint constructor
     *
     * @param string $tag Entrypoint tag
     * @param string|null $file File path
     * @param string|null $module Module name
     * @param string|null $extractor Extractor function
     * @param string|null $description Description
     */
    public function __construct(
        string $tag,
        ?string $file = null,
        ?string $module = null,
        ?string $extractor = null,
        ?string $description = null
    ) {
        $this->tag = $tag;
        $this->file = $file;
        $this->module = $module;
        $this->extractor = $extractor;
        $this->description = $description;
    }

    /**
     * Create from JSON data
     *
     * @param array $data JSON data
     * @return self
     */
    public static function fromArray(array $data): self
    {
        return new self(
            $data['tag'] ?? '',
            $data['file'] ?? null,
            $data['module'] ?? null,
            $data['extractor'] ?? null,
            $data['description'] ?? null
        );
    }
}
