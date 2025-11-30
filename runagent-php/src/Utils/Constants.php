<?php

namespace RunAgent\Utils;

/**
 * Constants used throughout the RunAgent SDK
 */
class Constants
{
    /**
     * Default base URL for remote RunAgent service
     */
    public const DEFAULT_BASE_URL = 'https://backend.run-agent.ai';
    
    /**
     * Default API prefix
     */
    public const DEFAULT_API_PREFIX = '/api/v1';
    
    /**
     * Default port for local agents
     */
    public const DEFAULT_LOCAL_PORT = 8450;
    
    /**
     * Default host for local agents
     */
    public const DEFAULT_LOCAL_HOST = '127.0.0.1';
    
    /**
     * Default timeout in seconds
     */
    public const DEFAULT_TIMEOUT_SECONDS = 300;
    
    /**
     * Default stream timeout in seconds
     */
    public const DEFAULT_STREAM_TIMEOUT = 600;
    
    /**
     * Local cache directory path (relative to home)
     */
    public const LOCAL_CACHE_DIRECTORY = '.runagent';
    
    /**
     * Database file name
     */
    public const DATABASE_FILE_NAME = 'runagent_local.db';
    
    /**
     * Environment variable names
     */
    public const ENV_API_KEY = 'RUNAGENT_API_KEY';
    public const ENV_BASE_URL = 'RUNAGENT_BASE_URL';
    public const ENV_LOCAL_AGENT = 'RUNAGENT_LOCAL';
    public const ENV_AGENT_HOST = 'RUNAGENT_HOST';
    public const ENV_AGENT_PORT = 'RUNAGENT_PORT';
    public const ENV_TIMEOUT = 'RUNAGENT_TIMEOUT';
    
    /**
     * User agent string
     *
     * @return string
     */
    public static function userAgent(): string
    {
        return 'runagent-php/0.1.0';
    }
}
