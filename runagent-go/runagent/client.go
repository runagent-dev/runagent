package runagent

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"reflect"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/websocket"

	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/constants"
	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/db"
)

// RunAgentClient is the main entry point for invoking RunAgent deployments.
type RunAgentClient struct {
	agentID       string
	entrypointTag string
	local         bool
	baseRESTURL   string
	baseSocketURL string
	apiKey        string
	timeoutSecs   int
	asyncDefault  bool
	extraParams   map[string]interface{}
	httpClient    *http.Client
}

// NewRunAgentClient creates a new client instance using the provided config.
func NewRunAgentClient(cfg Config) (*RunAgentClient, error) {
	if strings.TrimSpace(cfg.AgentID) == "" {
		return nil, newError(ErrorTypeValidation, "agent_id is required")
	}
	if strings.TrimSpace(cfg.EntrypointTag) == "" {
		return nil, newError(ErrorTypeValidation, "entrypoint_tag is required")
	}

	env := loadEnvConfig()

	local := resolveBool(cfg.Local, env.local, false)
	asyncDefault := resolveBool(cfg.AsyncExecution, nil, false)

	timeout := cfg.TimeoutSeconds
	if timeout <= 0 {
		timeout = env.timeoutSeconds
	}
	if timeout <= 0 {
		timeout = constants.DefaultTimeoutSeconds
	}

	apiKey := firstNonEmpty(cfg.APIKey, env.apiKey)
	baseURL := firstNonEmpty(cfg.BaseURL, env.baseURL, constants.DefaultBaseURL)

	var restBase, socketBase string
	var host string
	var port int
	if local {
		host = firstNonEmpty(cfg.Host, env.host)
		port = firstNonZero(cfg.Port, env.port)

		if host == "" || port == 0 {
			discoveredHost, discoveredPort, err := discoverLocalAgent(cfg.AgentID)
			if err != nil {
				return nil, err
			}
			if host == "" {
				host = discoveredHost
			}
			if port == 0 {
				port = discoveredPort
			}
		}

		if host == "" || port == 0 {
			return nil, newError(
				ErrorTypeValidation,
				"unable to resolve local host/port",
				withSuggestion("Pass Config.Host/Config.Port or ensure the agent is registered locally"),
			)
		}

		restBase = fmt.Sprintf("http://%s:%d%s", host, port, constants.DefaultAPIPrefix)
		socketBase = fmt.Sprintf("ws://%s:%d%s", host, port, constants.DefaultAPIPrefix)
	} else {
		var err error
		restBase, socketBase, err = normalizeRemoteBases(baseURL)
		if err != nil {
			return nil, err
		}
	}

	httpClient := cfg.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{
			Timeout: time.Duration(timeout) * time.Second,
		}
	}

	extra := cfg.ExtraParams
	if extra == nil {
		extra = map[string]interface{}{}
	}

	return &RunAgentClient{
		agentID:       cfg.AgentID,
		entrypointTag: cfg.EntrypointTag,
		local:         local,
		baseRESTURL:   restBase,
		baseSocketURL: socketBase,
		apiKey:        apiKey,
		timeoutSecs:   timeout,
		asyncDefault:  asyncDefault,
		extraParams:   extra,
		httpClient:    httpClient,
	}, nil
}

// Run invokes the agent using native Go-shaped arguments.
// Examples:
//  - positional: Run(ctx, Arg("q"), Arg(4))
//  - keyword:    Run(ctx, Kws(map[string]any{"m":3}))
//  - mixed:      Run(ctx, Args("q",4), Kw("m",3))
//  - struct:     Run(ctx, MyStruct{...}) -> kwargs via json tags
//  - single:     Run(ctx, "hello") -> ["hello"], {}
func (c *RunAgentClient) Run(ctx context.Context, values ...any) (interface{}, error) {
	// Guardrail: non-stream only
	if c.entrypointTag == "generic_stream" || c.entrypointTag == "stream" || strings.HasSuffix(strings.ToLower(c.entrypointTag), "_stream") {
		return nil, newError(
			ErrorTypeValidation,
			"stream entrypoint must be invoked with RunStream",
			withCode("STREAM_ENTRYPOINT"),
			withSuggestion("Use client.RunStream(...) for *_stream tags"),
		)
	}

	input, err := coerceToRunInput(values...)
	if err != nil {
		return nil, err
	}
	payload := input.toAPIPayload(c.entrypointTag, c.timeoutSecs, c.asyncDefault)

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, newError(ErrorTypeValidation, "failed to serialize request", withCause(err))
	}

	endpoint := fmt.Sprintf("%s/agents/%s/run", c.baseRESTURL, c.agentID)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return nil, newError(ErrorTypeUnknown, "failed to create request", withCause(err))
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", userAgent())
	if !c.local {
		if c.apiKey == "" {
			return nil, newError(
				ErrorTypeAuthentication,
				"api_key is required for remote runs",
				withSuggestion("Set RUNAGENT_API_KEY or pass Config.APIKey"),
			)
		}
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, newError(
			ErrorTypeConnection,
			"failed to reach RunAgent service",
			withCause(err),
			withSuggestion("Check your network connection or agent status"),
		)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, newError(ErrorTypeUnknown, "failed to read response body", withCause(err))
	}

	if resp.StatusCode != http.StatusOK {
		return nil, translateHTTPError(resp.StatusCode, respBody)
	}

	return parseRunResponse(resp.StatusCode, respBody)
}

// RunNative invokes the agent using native Go-shaped arguments without requiring RunInput.
// Usage:
//  - positional: RunNative(ctx, Arg("q"), Arg(4))
//  - keyword:    RunNative(ctx, Kws(map[string]any{"m": 3, "n": 4}))
//  - mixed:      RunNative(ctx, Args("q", 4), Kw("m", 3), Kw("n", 4))
//  - struct:     RunNative(ctx, MyStruct{...}) -> kwargs via json tags
//  - single:     RunNative(ctx, "hello") -> ["hello"], {}
func (c *RunAgentClient) RunNative(ctx context.Context, values ...any) (interface{}, error) {
	input, err := coerceToRunInput(values...)
	if err != nil {
		return nil, err
	}
	return c.Run(ctx, input)
}

// RunStream starts a streaming execution via WebSocket using native arguments.
func (c *RunAgentClient) RunStream(ctx context.Context, values ...any) (*StreamIterator, error) {
	// Guardrail: stream only
	if !(c.entrypointTag == "generic_stream" || c.entrypointTag == "stream" || strings.HasSuffix(strings.ToLower(c.entrypointTag), "_stream")) {
		return nil, newError(
			ErrorTypeValidation,
			"non-stream entrypoint must be invoked with Run",
			withCode("NON_STREAM_ENTRYPOINT"),
			withSuggestion("Use client.Run(...) for non-stream tags"),
		)
	}

	input, err := coerceToRunInput(values...)
	if err != nil {
		return nil, err
	}

	// Optional final StreamOptions can be passed via Kw("__timeout_seconds__", x)
	// but we keep defaults; consider functional options in future.
	timeout := constants.DefaultStreamTimeout
	payload := input.toAPIPayload(c.entrypointTag, timeout, false)
	payload.AsyncExecution = false

	data, err := json.Marshal(payload)
	if err != nil {
		return nil, newError(ErrorTypeValidation, "failed to serialize stream payload", withCause(err))
	}

	if !c.local && c.apiKey == "" {
		return nil, newError(
			ErrorTypeAuthentication,
			"api_key is required for remote streaming",
			withSuggestion("Set RUNAGENT_API_KEY or pass Config.APIKey"),
		)
	}

	endpoint := fmt.Sprintf("%s/agents/%s/run-stream", c.baseSocketURL, c.agentID)
	if !c.local && c.apiKey != "" {
		endpoint = appendToken(endpoint, c.apiKey)
	}

	dialer := websocket.Dialer{
		HandshakeTimeout: 30 * time.Second,
	}

	headers := http.Header{
		"User-Agent": []string{userAgent()},
	}

	conn, _, err := dialer.DialContext(ctx, endpoint, headers)
	if err != nil {
		return nil, newError(
			ErrorTypeConnection,
			"failed to open WebSocket connection",
			withCause(err),
		)
	}

	if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
		conn.Close()
		return nil, newError(ErrorTypeConnection, "failed to send stream bootstrap payload", withCause(err))
	}

	return newStreamIterator(conn), nil
}

// RunStreamNative starts a streaming execution using native Go-shaped arguments.
func (c *RunAgentClient) RunStreamNative(ctx context.Context, values ...any) (*StreamIterator, error) {
	input, err := coerceToRunInput(values...)
	if err != nil {
		return nil, err
	}
	return c.RunStream(ctx, input)
}

// ExtraParams returns the extra metadata provided at construction.
func (c *RunAgentClient) ExtraParams() map[string]interface{} {
	copyMap := make(map[string]interface{}, len(c.extraParams))
	for k, v := range c.extraParams {
		copyMap[k] = v
	}
	return copyMap
}

func parseRunResponse(status int, body []byte) (interface{}, error) {
	var envelope map[string]interface{}
	if err := json.Unmarshal(body, &envelope); err != nil {
		// Allow plain-string outputs.
		return decodeStructuredString(string(body)), nil
	}

	if errPayload := extractAPIError(envelope); errPayload != nil {
		return nil, newExecutionError(status, errPayload)
	}

	if data, ok := envelope["data"]; ok {
		if result := unwrapDataField(data); result != nil {
			// If the result is a structured object with payload, normalize it further
			if m, ok := result.(map[string]interface{}); ok {
				normalized := decodeStructuredObject(m)
				return normalized, nil
			}
			return result, nil
		}
	}

	// Payload-only structured responses
	if payload, exists := envelope["payload"]; exists {
		switch p := payload.(type) {
		case string:
			decoded := decodeStructuredString(p)
			return decoded, nil
		default:
			return p, nil
		}
	}

	if outputData, ok := envelope["output_data"]; ok {
		return outputData, nil
	}

	return envelope, nil
}

func extractAPIError(envelope map[string]interface{}) *apiErrorPayload {
	if envelope == nil {
		return nil
	}

	if rawErr, ok := envelope["error"]; ok {
		if parsed := parseAPIError(rawErr); parsed != nil {
			return parsed
		}
	}

	if success, ok := envelope["success"].(bool); ok && success {
		return nil
	}

	if success, ok := envelope["success"].(bool); ok && !success {
		message := "agent execution failed"
		if msg, ok := envelope["message"].(string); ok && msg != "" {
			message = msg
		}
		return &apiErrorPayload{
			Type:    ErrorTypeServer,
			Message: message,
		}
	}

	return nil
}

func parseAPIError(raw interface{}) *apiErrorPayload {
	switch val := raw.(type) {
	case nil:
		return nil
	case string:
		return &apiErrorPayload{
			Type:    ErrorTypeServer,
			Message: val,
		}
	case map[string]interface{}:
		payload := &apiErrorPayload{
			Type: ErrorTypeServer,
		}

		if t, ok := val["type"].(string); ok && t != "" {
			payload.Type = ErrorType(t)
		}
		if msg, ok := val["message"].(string); ok {
			payload.Message = msg
		}
		if code, ok := val["code"].(string); ok {
			payload.Code = code
		}
		if suggestion, ok := val["suggestion"].(string); ok {
			payload.Suggestion = suggestion
		}
		if details, ok := val["details"].(map[string]interface{}); ok {
			payload.Details = details
		}
		return payload
	default:
		return &apiErrorPayload{
			Type:    ErrorTypeServer,
			Message: fmt.Sprintf("%v", val),
		}
	}
}

func unwrapDataField(data interface{}) interface{} {
	switch typed := data.(type) {
	case string:
		return decodeStructuredString(typed)
	case map[string]interface{}:
		if resultData, ok := typed["result_data"].(map[string]interface{}); ok {
			if inner, exists := resultData["data"]; exists {
				return inner
			}
		}
		if inner, ok := typed["data"]; ok {
			return inner
		}
		if inner, ok := typed["content"]; ok {
			return inner
		}
		// Structured object with payload field
		return decodeStructuredObject(typed)
	default:
		return typed
	}
}

type envConfig struct {
	apiKey         string
	baseURL        string
	host           string
	port           int
	timeoutSeconds int
	local          *bool
}

func loadEnvConfig() envConfig {
	cfg := envConfig{}
	cfg.apiKey = strings.TrimSpace(os.Getenv(constants.EnvAPIKey))
	cfg.baseURL = strings.TrimSpace(os.Getenv(constants.EnvBaseURL))
	cfg.host = strings.TrimSpace(os.Getenv(constants.EnvAgentHost))

	if portStr := os.Getenv(constants.EnvAgentPort); portStr != "" {
		if port, err := strconv.Atoi(portStr); err == nil {
			cfg.port = port
		}
	}

	if timeoutStr := os.Getenv(constants.EnvTimeout); timeoutStr != "" {
		if timeout, err := strconv.Atoi(timeoutStr); err == nil {
			cfg.timeoutSeconds = timeout
		}
	}

	if localStr := os.Getenv(constants.EnvLocalAgent); localStr != "" {
		if local, err := strconv.ParseBool(localStr); err == nil {
			cfg.local = &local
		}
	}

	return cfg
}

func discoverLocalAgent(agentID string) (string, int, error) {
	svc, err := db.NewService("")
	if err != nil {
		return "", 0, newError(ErrorTypeConnection, "failed to open local agent registry", withCause(err))
	}
	defer svc.Close()

	agent, err := svc.GetAgent(agentID)
	if err != nil {
		return "", 0, newError(ErrorTypeServer, "failed to lookup agent in local database", withCause(err))
	}
	if agent == nil {
		return "", 0, newError(
			ErrorTypeValidation,
			fmt.Sprintf("agent %s was not found locally", agentID),
			withSuggestion("Start the agent locally or pass host/port overrides"),
		)
	}

	return agent.Host, agent.Port, nil
}

func normalizeRemoteBases(raw string) (string, string, error) {
	if raw == "" {
		raw = constants.DefaultBaseURL
	}

	if !strings.HasPrefix(raw, "http://") && !strings.HasPrefix(raw, "https://") {
		raw = "https://" + raw
	}

	trimmed := strings.TrimSuffix(raw, "/")

	restBase := trimmed + constants.DefaultAPIPrefix

	var socketBase string
	switch {
	case strings.HasPrefix(trimmed, "https://"):
		socketBase = "wss://" + strings.TrimPrefix(trimmed, "https://") + constants.DefaultAPIPrefix
	case strings.HasPrefix(trimmed, "http://"):
		socketBase = "ws://" + strings.TrimPrefix(trimmed, "http://") + constants.DefaultAPIPrefix
	default:
		return "", "", newError(ErrorTypeValidation, fmt.Sprintf("invalid base URL: %s", raw))
	}

	return restBase, socketBase, nil
}

func resolveBool(explicit *bool, fallback *bool, defaultValue bool) bool {
	switch {
	case explicit != nil:
		return *explicit
	case fallback != nil:
		return *fallback
	default:
		return defaultValue
	}
}

func firstNonEmpty(values ...string) string {
	for _, candidate := range values {
		if strings.TrimSpace(candidate) != "" {
			return strings.TrimSpace(candidate)
		}
	}
	return ""
}

func firstNonZero(values ...int) int {
	for _, candidate := range values {
		if candidate > 0 {
			return candidate
		}
	}
	return 0
}

func appendToken(uri, token string) string {
	if token == "" {
		return uri
	}
	parsed, err := url.Parse(uri)
	if err != nil {
		return uri
	}
	query := parsed.Query()
	query.Set("token", token)
	parsed.RawQuery = query.Encode()
	return parsed.String()
}

func translateHTTPError(status int, body []byte) error {
	apiErr := &apiErrorPayload{
		Type:    ErrorTypeServer,
		Message: fmt.Sprintf("server returned status %d", status),
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err == nil {
		if parsed := extractAPIError(payload); parsed != nil {
			apiErr = enrichErrorPayload(parsed)
		}
	}

	if status == http.StatusUnauthorized || status == http.StatusForbidden {
		apiErr.Type = ErrorTypeAuthentication
		if apiErr.Suggestion == "" {
			apiErr.Suggestion = "Set RUNAGENT_API_KEY or pass Config.APIKey"
		}
	} else if status >= 500 {
		apiErr.Type = ErrorTypeServer
	}

	return newExecutionError(status, apiErr)
}

func userAgent() string {
	return fmt.Sprintf("runagent-go/%s", Version)
}

// ---- Flexible argument tokens and coercion ----

type argToken struct{ v any }
type argsToken struct{ v []any }
type kwToken struct {
	k string
	v any
}
type kwsToken struct{ m map[string]any }

// Arg appends one positional argument.
func Arg(v any) argToken { return argToken{v: v} }

// Args appends multiple positional arguments.
func Args(v ...any) argsToken { return argsToken{v: v} }

// Kw adds one keyword argument.
func Kw(key string, value any) kwToken { return kwToken{k: key, v: value} }

// Kws merges many keyword arguments from a map.
func Kws(m map[string]any) kwsToken { return kwsToken{m: m} }

func coerceToRunInput(values ...any) (RunInput, error) {
	var input RunInput
	var haveArgs bool
	var haveKw bool

	appendArg := func(v any) {
		input.InputArgs = append(input.InputArgs, v)
		haveArgs = true
	}
	addKw := func(k string, v any) {
		if input.InputKwargs == nil {
			input.InputKwargs = map[string]any{}
		}
		input.InputKwargs[k] = v
		haveKw = true
	}

	for _, v := range values {
		switch t := v.(type) {
		case argToken:
			appendArg(t.v)
		case argsToken:
			for _, item := range t.v {
				appendArg(item)
			}
		case kwToken:
			addKw(t.k, t.v)
		case kwsToken:
			for k, val := range t.m {
				addKw(k, val)
			}
		case map[string]any:
			for k, val := range t {
				addKw(k, val)
			}
		default:
			// Reject raw []any to avoid ambiguity with Args(...).
			if isSliceOfAny(t) {
				return RunInput{}, newError(
					ErrorTypeValidation,
					"pass positional slice via Args(...), not raw []any",
					withSuggestion("Use runagent.Args(v1, v2, ...)"),
				)
			}
			// Structs→kwargs via json round-trip; primitives→single arg.
			if isStructLike(t) {
				m, err := structToMap(t)
				if err != nil {
					return RunInput{}, newError(ErrorTypeValidation, "failed to encode struct into kwargs", withCause(err))
				}
				for k, val := range m {
					addKw(k, val)
				}
			} else {
				appendArg(t)
			}
		}
	}

	// Ensure non-nil fields
	if !haveArgs {
		input.InputArgs = []any{}
	}
	if !haveKw {
		input.InputKwargs = map[string]any{}
	}

	return input, nil
}

func isSliceOfAny(v any) bool {
	rv := reflect.ValueOf(v)
	return rv.IsValid() && rv.Kind() == reflect.Slice && rv.Type().Elem().Kind() == reflect.Interface
}

func isStructLike(v any) bool {
	rv := reflect.ValueOf(v)
	if !rv.IsValid() {
		return false
	}
	k := rv.Kind()
	return k == reflect.Struct
}

func structToMap(v any) (map[string]any, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	return m, nil
}

// GetArchitecture fetches the agent architecture and normalizes both envelope and legacy formats.
func (c *RunAgentClient) GetArchitecture(ctx context.Context) (*AgentArchitecture, error) {
	endpoint := fmt.Sprintf("%s/agents/%s/architecture", c.baseRESTURL, c.agentID)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, newError(ErrorTypeUnknown, "failed to create request", withCause(err))
	}
	if !c.local {
		if c.apiKey == "" {
			return nil, newError(
				ErrorTypeAuthentication,
				"api_key is required for remote calls",
				withSuggestion("Set RUNAGENT_API_KEY or pass Config.APIKey"),
			)
		}
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	}
	req.Header.Set("User-Agent", userAgent())

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, newError(ErrorTypeConnection, "failed to reach RunAgent service", withCause(err))
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, newError(ErrorTypeUnknown, "failed to read response body", withCause(err))
	}

	if resp.StatusCode != http.StatusOK {
		return nil, translateHTTPError(resp.StatusCode, body)
	}

	// Try envelope format
	var envelope struct {
		Success bool `json:"success"`
		Data struct {
			AgentID     string       `json:"agent_id"`
			Entrypoints []EntryPoint `json:"entrypoints"`
		} `json:"data"`
		Message string      `json:"message"`
		Error   interface{} `json:"error"`
	}
	if err := json.Unmarshal(body, &envelope); err == nil && (envelope.Success || envelope.Message != "" || envelope.Error != nil) {
		if envelope.Success {
			if len(envelope.Data.Entrypoints) == 0 {
				return nil, newError(
					ErrorTypeValidation,
					"architecture missing entrypoints",
					withCode("ARCHITECTURE_MISSING"),
					withSuggestion("Redeploy the agent with entrypoints configured"),
				)
			}
			return &AgentArchitecture{
				AgentID:     envelope.Data.AgentID,
				Entrypoints: envelope.Data.Entrypoints,
			}, nil
		}
		if apiErr := parseAPIError(envelope.Error); apiErr != nil {
			return nil, newExecutionError(resp.StatusCode, apiErr)
		}
		return nil, newError(ErrorTypeServer, "failed to retrieve agent architecture")
	}

	// Fallback to legacy
	var legacy AgentArchitecture
	if err := json.Unmarshal(body, &legacy); err != nil {
		return nil, newError(ErrorTypeUnknown, "failed to decode architecture", withCause(err))
	}
	if len(legacy.Entrypoints) == 0 {
		return nil, newError(
			ErrorTypeValidation,
			"architecture missing entrypoints",
			withCode("ARCHITECTURE_MISSING"),
			withSuggestion("Redeploy the agent with entrypoints configured"),
		)
	}
	return &legacy, nil
}
