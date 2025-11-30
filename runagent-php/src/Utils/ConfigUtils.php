<?php

namespace RunAgent\Utils;

/**
 * Configuration utilities for loading from environment variables
 * 
 * Handles configuration precedence: explicit > env > default
 */
class ConfigUtils
{
    /**
     * Get API key from environment or return null
     *
     * @return string|null
     */
    public static function getApiKey(): ?string
    {
        return getenv(Constants::ENV_API_KEY) ?: null;
    }

    /**
     * Get base URL from environment or return default
     *
     * @return string
     */
    public static function getBaseUrl(): string
    {
        $env = getenv(Constants::ENV_BASE_URL);
        return $env ?: Constants::DEFAULT_BASE_URL;
    }

    /**
     * Get local flag from environment
     *
     * @return bool|null
     */
    public static function getLocal(): ?bool
    {
        $value = getenv(Constants::ENV_LOCAL_AGENT);
        if ($value === false) {
            return null;
        }
        return strtolower($value) === 'true';
    }

    /**
     * Get host from environment
     *
     * @return string|null
     */
    public static function getHost(): ?string
    {
        return getenv(Constants::ENV_AGENT_HOST) ?: null;
    }

    /**
     * Get port from environment
     *
     * @return int|null
     */
    public static function getPort(): ?int
    {
        $value = getenv(Constants::ENV_AGENT_PORT);
        if ($value === false) {
            return null;
        }
        $port = filter_var($value, FILTER_VALIDATE_INT);
        return $port !== false ? $port : null;
    }

    /**
     * Get timeout from environment
     *
     * @return int|null
     */
    public static function getTimeout(): ?int
    {
        $value = getenv(Constants::ENV_TIMEOUT);
        if ($value === false) {
            return null;
        }
        $timeout = filter_var($value, FILTER_VALIDATE_INT);
        return $timeout !== false ? $timeout : null;
    }

    /**
     * Resolve boolean with precedence: explicit > env > default
     *
     * @param bool|null $explicit Explicitly provided value
     * @param bool|null $env Environment value
     * @param bool $default Default value
     * @return bool
     */
    public static function resolveBool(?bool $explicit, ?bool $env, bool $default): bool
    {
        if ($explicit !== null) {
            return $explicit;
        }
        if ($env !== null) {
            return $env;
        }
        return $default;
    }

    /**
     * Get first non-empty string from array
     *
     * @param array $values Array of string values
     * @return string|null
     */
    public static function firstNonEmpty(array $values): ?string
    {
        foreach ($values as $value) {
            if ($value !== null && is_string($value) && trim($value) !== '') {
                return trim($value);
            }
        }
        return null;
    }

    /**
     * Get first non-zero integer from array
     *
     * @param array $values Array of integer values
     * @return int|null
     */
    public static function firstNonZero(array $values): ?int
    {
        foreach ($values as $value) {
            if ($value !== null && is_int($value) && $value > 0) {
                return $value;
            }
        }
        return null;
    }
}
