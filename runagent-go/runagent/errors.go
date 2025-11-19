package runagent

import (
	"fmt"
	"strings"
)

// ErrorType captures the standardized error taxonomy shared across SDKs.
type ErrorType string

const (
	ErrorTypeAuthentication ErrorType = "AUTHENTICATION_ERROR"
	ErrorTypePermission     ErrorType = "PERMISSION_ERROR"
	ErrorTypeConnection     ErrorType = "CONNECTION_ERROR"
	ErrorTypeValidation     ErrorType = "VALIDATION_ERROR"
	ErrorTypeServer         ErrorType = "SERVER_ERROR"
	ErrorTypeUnknown        ErrorType = "UNKNOWN_ERROR"
)

// RunAgentError is the root error type returned by the Go SDK.
type RunAgentError struct {
	Type       ErrorType
	Code       string
	Message    string
	Suggestion string
	Details    map[string]interface{}
	Cause      error
}

func (e *RunAgentError) Error() string {
	if e == nil {
		return "<nil>"
	}

	base := fmt.Sprintf("%s: %s", e.Type, e.Message)
	if e.Code != "" {
		base = fmt.Sprintf("%s (%s)", base, e.Code)
	}
	if e.Suggestion != "" {
		base = fmt.Sprintf("%s | suggestion: %s", base, e.Suggestion)
	}
	return base
}

// Unwrap exposes the wrapped cause when available.
func (e *RunAgentError) Unwrap() error {
	if e == nil {
		return nil
	}
	return e.Cause
}

// RunAgentExecutionError represents errors returned by the RunAgent service.
type RunAgentExecutionError struct {
	*RunAgentError
	HTTPStatus int
}

func newError(kind ErrorType, message string, opts ...func(*RunAgentError)) *RunAgentError {
	err := &RunAgentError{
		Type:    kind,
		Message: message,
	}
	for _, opt := range opts {
		opt(err)
	}
	return err
}

func withCode(code string) func(*RunAgentError) {
	return func(e *RunAgentError) {
		e.Code = code
	}
}

func withSuggestion(s string) func(*RunAgentError) {
	return func(e *RunAgentError) {
		e.Suggestion = s
	}
}

func withDetails(details map[string]interface{}) func(*RunAgentError) {
	return func(e *RunAgentError) {
		e.Details = details
	}
}

func withCause(err error) func(*RunAgentError) {
	return func(e *RunAgentError) {
		e.Cause = err
	}
}

func newExecutionError(status int, apiErr *apiErrorPayload) *RunAgentExecutionError {
	if apiErr == nil {
		apiErr = &apiErrorPayload{
			Type:    ErrorTypeUnknown,
			Message: "agent execution failed",
		}
	}

	apiErr = enrichErrorPayload(apiErr)

	runErr := &RunAgentError{
		Type:       apiErr.Type,
		Code:       apiErr.Code,
		Message:    apiErr.Message,
		Suggestion: apiErr.Suggestion,
		Details:    apiErr.Details,
	}
	if runErr.Type == "" {
		runErr.Type = ErrorTypeServer
	}
	return &RunAgentExecutionError{
		RunAgentError: runErr,
		HTTPStatus:    status,
	}
}

// enrichErrorPayload adds friendly suggestions for common error shapes.
func enrichErrorPayload(e *apiErrorPayload) *apiErrorPayload {
	if e == nil {
		return nil
	}
	msg := strings.ToLower(e.Message)
	code := strings.ToUpper(e.Code)

	switch {
	case strings.Contains(msg, "unexpected keyword argument"):
		if e.Suggestion == "" {
			e.Suggestion = "Check the entrypoint's expected parameter names. If your agent expects 'message', pass Kw(\"message\", ...)."
		}
	case strings.Contains(msg, "entrypoint") && strings.Contains(msg, "not found"):
		if e.Suggestion == "" {
			e.Suggestion = "Verify the entrypoint tag and use GetArchitecture(ctx) to list available tags."
		}
	case code == "AUTHENTICATION_ERROR":
		if e.Suggestion == "" {
			e.Suggestion = "Set RUNAGENT_API_KEY or pass Config.APIKey for remote calls."
		}
	case code == "NON_STREAM_ENTRYPOINT":
		if e.Suggestion == "" {
			e.Suggestion = "Use client.Run(...) for non-stream tags."
		}
	case code == "STREAM_ENTRYPOINT":
		if e.Suggestion == "" {
			e.Suggestion = "Use client.RunStream(...) for *_stream tags."
		}
	}
	return e
}

// formatFriendlyError renders a helpful panic message including suggestions when available.
func formatFriendlyError(err error) string {
	switch e := err.(type) {
	case *RunAgentExecutionError:
		if e.Suggestion != "" {
			return fmt.Sprintf("RunAgent error: %s (%s)\nSuggestion: %s", e.Message, e.Type, e.Suggestion)
		}
		return fmt.Sprintf("RunAgent error: %s (%s)", e.Message, e.Type)
	case *RunAgentError:
		if e.Suggestion != "" {
			return fmt.Sprintf("RunAgent error: %s (%s)\nSuggestion: %s", e.Message, e.Type, e.Suggestion)
		}
		return fmt.Sprintf("RunAgent error: %s (%s)", e.Message, e.Type)
	default:
		return fmt.Sprintf("RunAgent error: %v", err)
	}
}
