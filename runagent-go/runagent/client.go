package runagent

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
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

// Run invokes the agent using the REST API.
func (c *RunAgentClient) Run(ctx context.Context, input RunInput) (interface{}, error) {
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

// RunStream starts a streaming execution via WebSocket.
func (c *RunAgentClient) RunStream(ctx context.Context, input RunInput, opts ...StreamOptions) (*StreamIterator, error) {
	timeout := constants.DefaultStreamTimeout
	if len(opts) > 0 && opts[0].TimeoutSeconds > 0 {
		timeout = opts[0].TimeoutSeconds
	}

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
			return result, nil
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
		return typed
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
			apiErr = parsed
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
