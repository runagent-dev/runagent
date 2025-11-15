package runagent

import (
	"fmt"
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
