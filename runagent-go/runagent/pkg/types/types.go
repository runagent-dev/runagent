package types

import (
	"fmt"
	"time"
)

// RunAgentError represents errors in the RunAgent SDK
type RunAgentError struct {
	Type    string `json:"type"`
	Message string `json:"message"`
	Code    string `json:"code,omitempty"`
}

func (e *RunAgentError) Error() string {
	return fmt.Sprintf("%s: %s", e.Type, e.Message)
}

// Error constructors
func NewAuthenticationError(message string) *RunAgentError {
	return &RunAgentError{Type: "authentication", Message: message}
}

func NewValidationError(message string) *RunAgentError {
	return &RunAgentError{Type: "validation", Message: message}
}

func NewConnectionError(message string) *RunAgentError {
	return &RunAgentError{Type: "connection", Message: message}
}

func NewServerError(message string) *RunAgentError {
	return &RunAgentError{Type: "server", Message: message}
}

func NewDatabaseError(message string) *RunAgentError {
	return &RunAgentError{Type: "database", Message: message}
}

func NewConfigError(message string) *RunAgentError {
	return &RunAgentError{Type: "config", Message: message}
}

// EntryPoint represents an agent entrypoint
type EntryPoint struct {
	File       string                 `json:"file,omitempty"`
	Module     string                 `json:"module,omitempty"`
	Tag        string                 `json:"tag"`
	Name       string                 `json:"name,omitempty"`
	Description string                `json:"description,omitempty"`
	Extractor  map[string]interface{} `json:"extractor,omitempty"`
}

// AgentArchitecture represents agent configuration
type AgentArchitecture struct {
	AgentID     string       `json:"agent_id,omitempty"`
	Entrypoints []EntryPoint `json:"entrypoints"`
}

// AgentInputArgs represents input for agent execution
type AgentInputArgs struct {
	InputArgs   []interface{}          `json:"input_args"`
	InputKwargs map[string]interface{} `json:"input_kwargs"`
}

// AgentRunRequest represents a request to run an agent
type AgentRunRequest struct {
	InputData AgentInputArgs `json:"input_data"`
}

// AgentRunResponse represents the response from running an agent
type AgentRunResponse struct {
	Success       bool        `json:"success"`
	OutputData    interface{} `json:"output_data,omitempty"`
	Error         string      `json:"error,omitempty"`
	ExecutionTime float64     `json:"execution_time,omitempty"`
	AgentID       string      `json:"agent_id"`
}

// AgentInfo represents agent information
type AgentInfo struct {
	Message   string                 `json:"message"`
	Version   string                 `json:"version"`
	Host      string                 `json:"host"`
	Port      int                    `json:"port"`
	Config    map[string]interface{} `json:"config"`
	Endpoints map[string]string      `json:"endpoints"`
}

// HealthResponse represents a health check response
type HealthResponse struct {
	Status    string                 `json:"status"`
	Server    string                 `json:"server"`
	Timestamp string                 `json:"timestamp"`
	Version   string                 `json:"version"`
	Services  map[string]interface{} `json:"services,omitempty"`
}

// SafeMessage represents a WebSocket message
type SafeMessage struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"`
	Timestamp time.Time              `json:"timestamp"`
	Data      interface{}            `json:"data"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
	Error     string                 `json:"error,omitempty"`
}

// StreamChunk represents a streaming response chunk
type StreamChunk struct {
	Data  interface{}
	Error error
}
