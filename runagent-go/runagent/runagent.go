// runagent.go - Main SDK implementation
package runagent

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// Config represents the configuration for the RunAgent client
type Config struct {
	AgentID       string `json:"agent_id"`
	EntrypointTag string `json:"entrypoint_tag"`
	Local         bool   `json:"local,omitempty"`
	Host          string `json:"host,omitempty"`
	Port          int    `json:"port,omitempty"`
	APIKey        string `json:"api_key,omitempty"`
	BaseURL       string `json:"base_url,omitempty"`
	BaseSocketURL string `json:"base_socket_url,omitempty"`
	APIPrefix     string `json:"api_prefix,omitempty"`
}

// AgentArchitecture represents the structure of an agent
type AgentArchitecture struct {
	Entrypoints []Entrypoint `json:"entrypoints"`
}

// Entrypoint represents an agent entrypoint
type Entrypoint struct {
	Tag         string `json:"tag"`
	Name        string `json:"name,omitempty"`
	Description string `json:"description,omitempty"`
}

// APIResponse represents a response from the API
type APIResponse struct {
	Success    bool        `json:"success"`
	OutputData interface{} `json:"output_data,omitempty"`
	Error      string      `json:"error,omitempty"`
	Data       interface{} `json:"data,omitempty"`
}

// WebSocketMessage represents a WebSocket message
type WebSocketMessage struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"`
	Timestamp string                 `json:"timestamp"`
	Data      interface{}            `json:"data"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
	Error     string                 `json:"error,omitempty"`
}

// ExecutionRequest represents a request for agent execution
type ExecutionRequest struct {
	Action    string                 `json:"action"`
	AgentID   string                 `json:"agent_id"`
	InputData map[string]interface{} `json:"input_data"`
}

// RunAgentClient is the main client for interacting with RunAgent
type RunAgentClient struct {
	config       Config
	httpClient   *http.Client
	serializer   *CoreSerializer
	architecture *AgentArchitecture
	baseURL      string
	socketURL    string
}

// NewRunAgentClient creates a new RunAgent client
func NewRunAgentClient(config Config) *RunAgentClient {
	if config.APIPrefix == "" {
		config.APIPrefix = "/api/v1"
	}

	client := &RunAgentClient{
		config:     config,
		httpClient: &http.Client{Timeout: 120 * time.Second},
		serializer: NewCoreSerializer(),
	}

	if config.Local {
		host := config.Host
		if host == "" {
			host = "localhost"
		}
		port := config.Port
		if port == 0 {
			port = 8080
		}

		client.baseURL = fmt.Sprintf("http://%s:%d%s", host, port, config.APIPrefix)
		client.socketURL = fmt.Sprintf("ws://%s:%d%s", host, port, config.APIPrefix)
		fmt.Printf("🔌 Using local address: %s:%d\n", host, port)
	} else {
		if config.BaseURL != "" {
			client.baseURL = strings.TrimSuffix(config.BaseURL, "/") + config.APIPrefix
		}
		if config.BaseSocketURL != "" {
			client.socketURL = strings.TrimSuffix(config.BaseSocketURL, "/") + config.APIPrefix
		}
	}

	return client
}

// Initialize initializes the client by fetching agent architecture
func (c *RunAgentClient) Initialize(ctx context.Context) error {
	architecture, err := c.getAgentArchitecture(ctx)
	if err != nil {
		return fmt.Errorf("failed to initialize agent: %w", err)
	}

	// Verify entrypoint exists
	found := false
	for _, entrypoint := range architecture.Entrypoints {
		if entrypoint.Tag == c.config.EntrypointTag {
			found = true
			break
		}
	}

	if !found {
		return fmt.Errorf("entrypoint `%s` not found in agent %s", c.config.EntrypointTag, c.config.AgentID)
	}

	c.architecture = architecture
	return nil
}

// Run executes the agent with the given input
func (c *RunAgentClient) Run(ctx context.Context, inputKwargs map[string]interface{}) (interface{}, error) {
	if strings.HasSuffix(c.config.EntrypointTag, "_stream") {
		return c.runStream(ctx, inputKwargs)
	}
	return c.run(ctx, inputKwargs)
}

// run executes the agent via REST API
func (c *RunAgentClient) run(ctx context.Context, inputKwargs map[string]interface{}) (interface{}, error) {
	fmt.Printf("🤖 Executing agent: %s\n", c.config.AgentID)

	// Create the correct request format that matches what the server expects
	requestData := map[string]interface{}{
		"input_data": map[string]interface{}{
			"input_args":   []interface{}{},
			"input_kwargs": inputKwargs,
		},
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	fmt.Printf("🔍 Request payload: %s\n", string(jsonData))

	url := fmt.Sprintf("%s/agents/%s/execute/%s", c.baseURL, c.config.AgentID, c.config.EntrypointTag)
	fmt.Printf("🔗 Request URL: %s\n", url)

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	if c.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.APIKey)
		req.Header.Set("User-Agent", "RunAgent-Go/1.0")
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	fmt.Printf("📋 Response status: %d\n", resp.StatusCode)
	fmt.Printf("📋 Response body: %s\n", string(body))

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP error %d: %s", resp.StatusCode, string(body))
	}

	// Try to parse as APIResponse first
	var apiResp APIResponse
	if err := json.Unmarshal(body, &apiResp); err != nil {
		// If that fails, try to parse as generic JSON
		var genericResp interface{}
		if err2 := json.Unmarshal(body, &genericResp); err2 != nil {
			return nil, fmt.Errorf("failed to unmarshal response: %w", err)
		}
		return genericResp, nil
	}

	if !apiResp.Success && apiResp.Error != "" {
		return nil, fmt.Errorf("agent execution failed: %s", apiResp.Error)
	}

	fmt.Println("✅ Agent execution completed!")

	// Return the appropriate data field
	if apiResp.OutputData != nil {
		return c.serializer.DeserializeObject(apiResp.OutputData, false), nil
	}
	if apiResp.Data != nil {
		return c.serializer.DeserializeObject(apiResp.Data, false), nil
	}

	return apiResp, nil
}

// runStream executes the agent via WebSocket for streaming
func (c *RunAgentClient) runStream(ctx context.Context, inputKwargs map[string]interface{}) (*StreamIterator, error) {
	wsURL := fmt.Sprintf("%s/agents/%s/execute/%s", c.socketURL, c.config.AgentID, c.config.EntrypointTag)

	dialer := websocket.Dialer{
		HandshakeTimeout: 30 * time.Second,
	}

	var headers http.Header
	if c.config.APIKey != "" {
		headers = http.Header{
			"Authorization": []string{"Bearer " + c.config.APIKey},
			"User-Agent":    []string{"RunAgent-Go/1.0"},
		}
	}

	conn, _, err := dialer.DialContext(ctx, wsURL, headers)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to WebSocket: %w", err)
	}

	// Send start message with correct format
	request := ExecutionRequest{
		Action:  "start_stream",
		AgentID: c.config.AgentID,
		InputData: map[string]interface{}{
			"input_args":   []interface{}{},
			"input_kwargs": inputKwargs,
		},
	}

	startMsg := WebSocketMessage{
		ID:        "stream_start",
		Type:      "status",
		Timestamp: time.Now().Format(time.RFC3339),
		Data:      request,
	}

	msgData, err := c.serializer.SerializeMessage(startMsg)
	if err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to serialize start message: %w", err)
	}

	if err := conn.WriteMessage(websocket.TextMessage, []byte(msgData)); err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to send start message: %w", err)
	}

	return NewStreamIterator(conn, c.serializer), nil
}

// getAgentArchitecture fetches the agent architecture
func (c *RunAgentClient) getAgentArchitecture(ctx context.Context) (*AgentArchitecture, error) {
	url := fmt.Sprintf("%s/agents/%s/architecture", c.baseURL, c.config.AgentID)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Accept", "application/json")
	if c.config.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.config.APIKey)
		req.Header.Set("User-Agent", "RunAgent-Go/1.0")
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP error %d: %s", resp.StatusCode, string(body))
	}

	var architecture AgentArchitecture
	if err := json.Unmarshal(body, &architecture); err != nil {
		return nil, fmt.Errorf("failed to unmarshal architecture: %w", err)
	}

	return &architecture, nil
}

// StreamIterator handles streaming responses
type StreamIterator struct {
	conn       *websocket.Conn
	serializer *CoreSerializer
	finished   bool
	err        error
}

// NewStreamIterator creates a new stream iterator
func NewStreamIterator(conn *websocket.Conn, serializer *CoreSerializer) *StreamIterator {
	return &StreamIterator{
		conn:       conn,
		serializer: serializer,
	}
}

// Next returns the next item from the stream
func (s *StreamIterator) Next(ctx context.Context) (interface{}, bool, error) {
	if s.finished || s.err != nil {
		return nil, false, s.err
	}

	select {
	case <-ctx.Done():
		s.finished = true
		s.conn.Close()
		return nil, false, ctx.Err()
	default:
	}

	_, messageData, err := s.conn.ReadMessage()
	if err != nil {
		s.finished = true
		s.err = fmt.Errorf("failed to read WebSocket message: %w", err)
		return nil, false, s.err
	}

	fmt.Printf("received=> %s\n", string(messageData))

	msg, err := s.serializer.DeserializeMessage(string(messageData))
	if err != nil {
		s.finished = true
		s.err = fmt.Errorf("failed to deserialize message: %w", err)
		return nil, false, s.err
	}

	if msg.Error != "" {
		s.finished = true
		s.err = fmt.Errorf("stream error: %s", msg.Error)
		return nil, false, s.err
	}

	if msg.Type == "status" {
		if data, ok := msg.Data.(map[string]interface{}); ok {
			if status, ok := data["status"].(string); ok {
				if status == "stream_completed" {
					s.finished = true
					return nil, false, nil
				} else if status == "stream_started" {
					return s.Next(ctx) // Skip this message and get the next one
				}
			}
		}
	} else if msg.Type == "ERROR" {
		s.finished = true
		s.err = fmt.Errorf("agent error: %v", msg.Data)
		return nil, false, s.err
	}

	return msg.Data, true, nil
}

// Close closes the stream iterator
func (s *StreamIterator) Close() error {
	s.finished = true
	return s.conn.Close()
}

// CoreSerializer handles serialization/deserialization
type CoreSerializer struct{}

// NewCoreSerializer creates a new core serializer
func NewCoreSerializer() *CoreSerializer {
	return &CoreSerializer{}
}

// SerializeMessage serializes a WebSocket message
func (s *CoreSerializer) SerializeMessage(message WebSocketMessage) (string, error) {
	messageDict := map[string]interface{}{
		"id":        message.ID,
		"type":      message.Type,
		"timestamp": message.Timestamp,
		"data":      message.Data,
		"metadata":  message.Metadata,
	}

	data, err := json.Marshal(messageDict)
	if err != nil {
		fallback := map[string]interface{}{
			"id":        message.ID,
			"type":      message.Type,
			"timestamp": message.Timestamp,
			"data":      map[string]interface{}{"error": fmt.Sprintf("Serialization failed: %s", err.Error())},
			"error":     fmt.Sprintf("Serialization Error: %s", err.Error()),
		}
		data, _ = json.Marshal(fallback)
	}

	return string(data), nil
}

// DeserializeMessage deserializes a WebSocket message
func (s *CoreSerializer) DeserializeMessage(jsonStr string) (*WebSocketMessage, error) {
	var data map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &data); err != nil {
		return nil, fmt.Errorf("invalid JSON: %w", err)
	}

	msg := &WebSocketMessage{}

	if id, ok := data["id"].(string); ok {
		msg.ID = id
	}
	if msgType, ok := data["type"].(string); ok {
		msg.Type = msgType
	}
	if timestamp, ok := data["timestamp"].(string); ok {
		msg.Timestamp = timestamp
	}
	if msgData, ok := data["data"]; ok {
		msg.Data = msgData
	}
	if metadata, ok := data["metadata"].(map[string]interface{}); ok {
		msg.Metadata = metadata
	}
	if errorMsg, ok := data["error"].(string); ok {
		msg.Error = errorMsg
	}

	return msg, nil
}

// DeserializeObject deserializes a JSON object
func (s *CoreSerializer) DeserializeObject(jsonResp interface{}, reconstruct bool) interface{} {
	return jsonResp // Simple pass-through for now
}
