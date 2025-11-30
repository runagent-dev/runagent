<?php

namespace RunAgent\Errors;

use Exception;

/**
 * Base exception class for all RunAgent errors
 * 
 * All RunAgent exceptions carry code, message, suggestion, and optional details
 * matching the SDK checklist requirements.
 */
class RunAgentError extends Exception
{
    /**
     * @var string Error code (e.g., 'AUTHENTICATION_ERROR', 'VALIDATION_ERROR')
     */
    protected string $errorCode;
    
    /**
     * @var string|null Helpful suggestion for resolving the error
     */
    protected ?string $suggestion;
    
    /**
     * @var array|null Additional error details
     */
    protected ?array $details;

    /**
     * RunAgentError constructor
     *
     * @param string $code Error code from ErrorCodes constants
     * @param string $message Human-readable error message
     * @param string|null $suggestion Suggestion for resolving the error
     * @param array|null $details Additional error context
     */
    public function __construct(
        string $code,
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct($message);
        $this->errorCode = $code;
        $this->suggestion = $suggestion;
        $this->details = $details;
    }

    /**
     * Get the error code
     *
     * @return string
     */
    public function getErrorCode(): string
    {
        return $this->errorCode;
    }

    /**
     * Get the suggestion
     *
     * @return string|null
     */
    public function getSuggestion(): ?string
    {
        return $this->suggestion;
    }

    /**
     * Get additional details
     *
     * @return array|null
     */
    public function getDetails(): ?array
    {
        return $this->details;
    }

    /**
     * Format the error as a string with code, message, and suggestion
     *
     * @return string
     */
    public function __toString(): string
    {
        $str = "[{$this->errorCode}] {$this->message}";
        if ($this->suggestion !== null) {
            $str .= "\nSuggestion: {$this->suggestion}";
        }
        return $str;
    }
}

/**
 * Execution error raised when agent execution fails
 */
class RunAgentExecutionError extends RunAgentError
{
}

/**
 * Authentication error (401, 403)
 */
class AuthenticationError extends RunAgentError
{
    public function __construct(
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct(ErrorCodes::AUTHENTICATION_ERROR, $message, $suggestion, $details);
    }
}

/**
 * Permission error (403)
 */
class PermissionError extends RunAgentError
{
    public function __construct(
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct(ErrorCodes::PERMISSION_ERROR, $message, $suggestion, $details);
    }
}

/**
 * Connection error (network, DNS, TLS issues)
 */
class ConnectionError extends RunAgentError
{
    public function __construct(
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct(ErrorCodes::CONNECTION_ERROR, $message, $suggestion, $details);
    }
}

/**
 * Validation error (400, 422, bad config)
 */
class ValidationError extends RunAgentError
{
    public function __construct(
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct(ErrorCodes::VALIDATION_ERROR, $message, $suggestion, $details);
    }
}

/**
 * Server error (5xx)
 */
class ServerError extends RunAgentError
{
    public function __construct(
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct(ErrorCodes::SERVER_ERROR, $message, $suggestion, $details);
    }
}

/**
 * Unknown error
 */
class UnknownError extends RunAgentError
{
    public function __construct(
        string $message,
        ?string $suggestion = null,
        ?array $details = null
    ) {
        parent::__construct(ErrorCodes::UNKNOWN_ERROR, $message, $suggestion, $details);
    }
}

/**
 * Error codes matching the checklist taxonomy
 */
class ErrorCodes
{
    public const AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR';
    public const PERMISSION_ERROR = 'PERMISSION_ERROR';
    public const CONNECTION_ERROR = 'CONNECTION_ERROR';
    public const VALIDATION_ERROR = 'VALIDATION_ERROR';
    public const SERVER_ERROR = 'SERVER_ERROR';
    public const UNKNOWN_ERROR = 'UNKNOWN_ERROR';
    public const AGENT_NOT_FOUND_LOCAL = 'AGENT_NOT_FOUND_LOCAL';
    public const AGENT_NOT_FOUND_REMOTE = 'AGENT_NOT_FOUND_REMOTE';
    public const STREAM_ENTRYPOINT = 'STREAM_ENTRYPOINT';
    public const NON_STREAM_ENTRYPOINT = 'NON_STREAM_ENTRYPOINT';
    public const ARCHITECTURE_MISSING = 'ARCHITECTURE_MISSING';
}
