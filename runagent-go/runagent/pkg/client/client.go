package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/config"
	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/db"
	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/types"
)

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

// StreamIterator handles streaming responses
type StreamIterator struct {
	conn       *websocket.Conn
	serializer *CoreSerializer
	finished   bool
	err        error
}

// CoreSerializer handles serialization/deserialization
type CoreSerializer struct{}

// Client represents a RunAgent client
type Client struct {
	agentID       string
	entrypointTag string
	local         bool
	baseURL       string
	socketURL     string
	httpClient    *http.Client
	dbService     *db.Service
	serializer    *CoreSerializer
}

// New creates a new RunAgent client
func New(agentID, entrypointTag string, local bool) (*Client, error) {
	client := &Client{
		agentID:       agentID,
		entrypointTag: entrypointTag,
		local:         local,
		httpClient: &http.Client{
			Timeout: 5 * time.Minute, // Increased for long-running agents
		},
		serializer: NewCoreSerializer(),
	}

	if local {
		// Try to find agent in database
		dbService, err := db.NewService("")
		if err != nil {
			return nil, fmt.Errorf("failed to initialize database: %w", err)
		}

		agent, err := dbService.GetAgent(agentID)
		if err != nil {
			dbService.Close()
			return nil, fmt.Errorf("failed to get agent from database: %w", err)
		}

		if agent == nil {
			dbService.Close()
			return nil, types.NewValidationError(fmt.Sprintf("Agent %s not found in local database", agentID))
		}

		client.baseURL = fmt.Sprintf("http://%s:%d", agent.Host, agent.Port)
		client.socketURL = fmt.Sprintf("ws://%s:%d", agent.Host, agent.Port)
		client.dbService = dbService
	} else {
		// Use remote configuration
		cfg, err := config.Load()
		if err != nil {
			return nil, fmt.Errorf("failed to load config: %w", err)
		}
		client.baseURL = cfg.BaseURL
		// Construct WebSocket URL from base URL
		if strings.HasPrefix(cfg.BaseURL, "https://") {
			client.socketURL = strings.Replace(cfg.BaseURL, "https://", "wss://", 1)
		} else {
			client.socketURL = strings.Replace(cfg.BaseURL, "http://", "ws://", 1)
		}
	}

	return client, nil
}

// NewWithAddress creates a client with explicit address
func NewWithAddress(agentID, entrypointTag string, local bool, host string, port int) (*Client, error) {
	client := &Client{
		agentID:       agentID,
		entrypointTag: entrypointTag,
		local:         local,
		httpClient: &http.Client{
			Timeout: 5 * time.Minute, // Increased for long-running agents
		},
		serializer: NewCoreSerializer(),
	}

	if local {
		client.baseURL = fmt.Sprintf("http://%s:%d", host, port)
		client.socketURL = fmt.Sprintf("ws://%s:%d", host, port)
	} else {
		cfg, err := config.Load()
		if err != nil {
			return nil, fmt.Errorf("failed to load config: %w", err)
		}
		client.baseURL = cfg.BaseURL
		// Construct WebSocket URL from base URL
		if strings.HasPrefix(cfg.BaseURL, "https://") {
			client.socketURL = strings.Replace(cfg.BaseURL, "https://", "wss://", 1)
		} else {
			client.socketURL = strings.Replace(cfg.BaseURL, "http://", "ws://", 1)
		}
	}

	return client, nil
}

// Close closes the client and any associated resources
func (c *Client) Close() error {
	if c.dbService != nil {
		return c.dbService.Close()
	}
	return nil
}

// Run executes the agent with the given input
func (c *Client) Run(ctx context.Context, input map[string]interface{}) (interface{}, error) {
	if c.entrypointTag == "generic_stream" || c.entrypointTag == "stream" || strings.HasSuffix(c.entrypointTag, "_stream") {
		return nil, types.NewValidationError("Use RunStream for streaming entrypoints")
	}

	// For LangGraph agents, the input should be passed directly as the first argument
	// The current structure wraps it incorrectly
	var request map[string]interface{}

	// Check if this is a generic entrypoint (LangGraph)
	if c.entrypointTag == "generic" {
		// For LangGraph, pass the input directly as the first positional argument
		request = map[string]interface{}{
			"input_data": map[string]interface{}{
				"input_args":   []interface{}{input},     // Pass input as first argument
				"input_kwargs": map[string]interface{}{}, // Empty kwargs
			},
		}
	} else {
		// For other entrypoints, use the original structure
		request = map[string]interface{}{
			"input_data": map[string]interface{}{
				"input_args":   []interface{}{},
				"input_kwargs": input,
			},
		}
	}

	requestBody, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Debug output
	fmt.Printf("Request body: %s\n", string(requestBody))

	url := fmt.Sprintf("%s/api/v1/agents/%s/execute/%s",
		c.baseURL, c.agentID, c.entrypointTag)

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(requestBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	// Increase timeout for potentially long-running agents
	client := &http.Client{
		Timeout: 5 * time.Minute, // Increased from 30 seconds
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, types.NewConnectionError(fmt.Sprintf("Failed to execute request: %v", err))
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	// Debug output
	fmt.Printf("Response status: %d\n", resp.StatusCode)
	fmt.Printf("Response body: %s\n", string(body))

	if resp.StatusCode != http.StatusOK {
		return nil, types.NewServerError(fmt.Sprintf("Server returned status %d: %s", resp.StatusCode, string(body)))
	}

	// Handle empty response body
	if len(body) == 0 {
		return nil, types.NewServerError("Server returned empty response")
	}

	// Parse response as generic map to handle different response formats
	var response map[string]interface{}
	if err := json.Unmarshal(body, &response); err != nil {
		// If JSON parsing fails, return the raw response
		fmt.Printf("Failed to parse JSON response, returning raw body: %v\n", err)
		return string(body), nil
	}

	// Check for success field
	if success, exists := response["success"]; exists {
		if successBool, ok := success.(bool); ok && !successBool {
			if errorMsg, exists := response["error"]; exists {
				return nil, types.NewServerError(fmt.Sprintf("%v", errorMsg))
			}
			return nil, types.NewServerError("Request failed with no error message")
		}
	}

	// Handle data field (simplified structured output or legacy execution payload)
	if dataField, exists := response["data"]; exists {
		switch data := dataField.(type) {
		case string:
			return c.serializer.DeserializeStructuredString(data), nil
		case map[string]interface{}:
			if resultData, ok := data["result_data"].(map[string]interface{}); ok {
				if output, ok := resultData["data"]; ok {
					return c.serializer.DeserializeObject(output, false), nil
				}
			}
		}
	}

	// Legacy fallback: return output_data if it exists
	if outputData, exists := response["output_data"]; exists {
		return c.serializer.DeserializeObject(outputData, false), nil
	}

	return response, nil
}

// RunStream executes the agent with streaming response using WebSocket
func (c *Client) RunStream(ctx context.Context, input map[string]interface{}) (*StreamIterator, error) {
	wsURL := fmt.Sprintf("%s/api/v1/agents/%s/execute/%s", c.socketURL, c.agentID, c.entrypointTag)

	dialer := websocket.Dialer{
		HandshakeTimeout: 30 * time.Second,
	}

	var headers http.Header
	// Add any authentication headers if needed
	headers = http.Header{
		"User-Agent": []string{"RunAgent-Go/1.0"},
	}

	conn, _, err := dialer.DialContext(ctx, wsURL, headers)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to WebSocket: %w", err)
	}

	// Send start message with correct format
	var inputData map[string]interface{}
	if c.entrypointTag == "generic" || strings.HasSuffix(c.entrypointTag, "_stream") {
		// For LangGraph streaming, pass input as first argument
		inputData = map[string]interface{}{
			"input_args":   []interface{}{input},
			"input_kwargs": map[string]interface{}{},
		}
	} else {
		// For other streaming entrypoints
		inputData = map[string]interface{}{
			"input_args":   []interface{}{},
			"input_kwargs": input,
		}
	}

	request := ExecutionRequest{
		Action:    "start_stream",
		AgentID:   c.agentID,
		InputData: inputData,
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

// HealthCheck checks if the agent is healthy
func (c *Client) HealthCheck(ctx context.Context) (bool, error) {
	url := fmt.Sprintf("%s/health", c.baseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return false, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return false, types.NewConnectionError(fmt.Sprintf("Health check failed: %v", err))
	}
	defer resp.Body.Close()

	return resp.StatusCode == http.StatusOK, nil
}

// GetAgentArchitecture retrieves the agent's architecture information
func (c *Client) GetAgentArchitecture(ctx context.Context) (*types.AgentArchitecture, error) {
	url := fmt.Sprintf("%s/api/v1/agents/%s/architecture", c.baseURL, c.agentID)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, types.NewConnectionError(fmt.Sprintf("Failed to get architecture: %v", err))
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, types.NewServerError(fmt.Sprintf("Server returned status %d", resp.StatusCode))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read architecture response: %w", err)
	}

	var envelope struct {
		Success bool `json:"success"`
		Data struct {
			AgentID     string             `json:"agent_id"`
			Entrypoints []types.EntryPoint `json:"entrypoints"`
		} `json:"data"`
		Message string      `json:"message"`
		Error   interface{} `json:"error"`
	}

	if err := json.Unmarshal(body, &envelope); err == nil && (envelope.Success || envelope.Message != "" || envelope.Error != nil) {
		if envelope.Success {
			architecture := &types.AgentArchitecture{
				AgentID:     envelope.Data.AgentID,
				Entrypoints: envelope.Data.Entrypoints,
			}
			return architecture, nil
		}

		var message string
		switch errInfo := envelope.Error.(type) {
		case map[string]interface{}:
			if m, ok := errInfo["message"].(string); ok {
				message = m
			}
		case string:
			message = errInfo
		}

		if message == "" {
			message = envelope.Message
		}
		if message == "" {
			message = "failed to retrieve agent architecture"
		}

		return nil, types.NewServerError(message)
	}

	// Fallback to legacy format without envelope
	var architecture types.AgentArchitecture
	if err := json.Unmarshal(body, &architecture); err != nil {
		return nil, fmt.Errorf("failed to decode architecture: %w", err)
	}

	return &architecture, nil
}

// AgentID returns the agent ID
func (c *Client) AgentID() string {
	return c.agentID
}

// EntrypointTag returns the entrypoint tag
func (c *Client) EntrypointTag() string {
	return c.entrypointTag
}

// IsLocal returns whether this is a local client
func (c *Client) IsLocal() bool {
	return c.local
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

// NewCoreSerializer creates a new core serializer
func NewCoreSerializer() *CoreSerializer {
	return &CoreSerializer{}
}

// DeserializeStructuredString converts structured serializer output to native Go types
func (s *CoreSerializer) DeserializeStructuredString(structured string) interface{} {
	var structuredMap map[string]interface{}
	if err := json.Unmarshal([]byte(structured), &structuredMap); err != nil {
		if unquoted, err2 := strconv.Unquote(structured); err2 == nil {
			return unquoted
		}
		return structured
	}

	payload, payloadExists := structuredMap["payload"]
	if !payloadExists {
		return structuredMap
	}

	switch p := payload.(type) {
	case string:
		if len(p) > 0 {
			var decoded interface{}
			if err := json.Unmarshal([]byte(p), &decoded); err == nil {
				return decoded
			}
			if unquoted, err := strconv.Unquote(p); err == nil {
				return unquoted
			}
		}
		return p
	default:
		return p
	}
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
	if str, ok := jsonResp.(string); ok {
		return s.DeserializeStructuredString(str)
	}
	return jsonResp // Simple pass-through for now
}
