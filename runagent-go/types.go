package runagent

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// Config captures initialization options for RunAgentClient.
// Field precedence: explicit Config values override environment variables,
// which override library defaults.
type Config struct {
	AgentID        string
	EntrypointTag  string
	Local          *bool
	Host           string
	Port           int
	BaseURL        string
	APIKey         string
	TimeoutSeconds int
	AsyncExecution *bool
	ExtraParams    map[string]interface{}
	HTTPClient     *http.Client
}

// RunInput describes a run invocation payload.
type RunInput struct {
	InputArgs      []interface{}
	InputKwargs    map[string]interface{}
	TimeoutSeconds int
	AsyncExecution *bool
}

// StreamOptions allow customizing RunStream behavior.
type StreamOptions struct {
	TimeoutSeconds int
}

// Bool is a helper to create *bool literals inline.
func Bool(v bool) *bool { return &v }

type apiRunRequest struct {
	EntrypointTag  string                 `json:"entrypoint_tag"`
	InputArgs      []interface{}          `json:"input_args"`
	InputKwargs    map[string]interface{} `json:"input_kwargs"`
	TimeoutSeconds int                    `json:"timeout_seconds"`
	AsyncExecution bool                   `json:"async_execution,omitempty"`
}

type apiErrorPayload struct {
	Type       ErrorType              `json:"type"`
	Code       string                 `json:"code"`
	Message    string                 `json:"message"`
	Suggestion string                 `json:"suggestion"`
	Details    map[string]interface{} `json:"details"`
}

type streamFrame struct {
	Type    string          `json:"type"`
	Status  string          `json:"status"`
	Content json.RawMessage `json:"content"`
	Data    json.RawMessage `json:"data"`
	Error   json.RawMessage `json:"error"`
}

// EntryPoint describes a deployable entrypoint.
type EntryPoint struct {
	File        string                 `json:"file,omitempty"`
	Module      string                 `json:"module,omitempty"`
	Tag         string                 `json:"tag"`
	Name        string                 `json:"name,omitempty"`
	Description string                 `json:"description,omitempty"`
	Extractor   map[string]interface{} `json:"extractor,omitempty"`
}

// AgentArchitecture provides entrypoint metadata for an agent.
type AgentArchitecture struct {
	AgentID     string       `json:"agent_id,omitempty"`
	Entrypoints []EntryPoint `json:"entrypoints"`
}

func (i RunInput) toAPIPayload(entrypoint string, fallbackTimeout int, defaultAsync bool) apiRunRequest {
	timeout := fallbackTimeout
	if i.TimeoutSeconds > 0 {
		timeout = i.TimeoutSeconds
	}

	async := defaultAsync
	if i.AsyncExecution != nil {
		async = *i.AsyncExecution
	}

	args := i.InputArgs
	if args == nil {
		args = []interface{}{}
	}

	kwargs := i.InputKwargs
	if kwargs == nil {
		kwargs = map[string]interface{}{}
	}

	return apiRunRequest{
		EntrypointTag:  entrypoint,
		InputArgs:      args,
		InputKwargs:    kwargs,
		TimeoutSeconds: timeout,
		AsyncExecution: async,
	}
}

func decodeStructuredString(value string) interface{} {
	if value == "" {
		return value
	}

	var decoded interface{}
	if err := json.Unmarshal([]byte(value), &decoded); err == nil {
		return decoded
	}

	var unquoted string
	if err := json.Unmarshal([]byte(fmt.Sprintf("%q", value)), &unquoted); err == nil {
		return unquoted
	}

	return value
}

// decodeStructuredObject handles objects that may contain a "payload" field
// where payload can be a stringified JSON or native JSON. This mirrors the
// normalization in other SDKs so callers get the inner content directly.
func decodeStructuredObject(obj map[string]interface{}) interface{} {
	if payload, ok := obj["payload"]; ok {
		switch p := payload.(type) {
		case string:
			return decodeStructuredString(p)
		default:
			return p
		}
	}
	return obj
}
