package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/types"
)

// Server represents a local RunAgent server
type Server struct {
	agentID   string
	agentPath string
	host      string
	port      int
	server    *http.Server
}

// New creates a new local server
func New(agentID, agentPath, host string, port int) (*Server, error) {
	s := &Server{
		agentID:   agentID,
		agentPath: agentPath,
		host:      host,
		port:      port,
	}

	router := s.setupRoutes()

	s.server = &http.Server{
		Addr:    fmt.Sprintf("%s:%d", host, port),
		Handler: router,
	}

	return s, nil
}

// setupRoutes configures the HTTP routes
func (s *Server) setupRoutes() *mux.Router {
	router := mux.NewRouter()

	// CORS middleware
	router.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}

			next.ServeHTTP(w, r)
		})
	})

	// Root endpoint
	router.HandleFunc("/", s.handleRoot).Methods("GET")

	// Health check
	router.HandleFunc("/health", s.handleHealth).Methods("GET")

	// API endpoints
	api := router.PathPrefix("/api/v1").Subrouter()
	api.HandleFunc("/health", s.handleHealth).Methods("GET")
	api.HandleFunc("/agents/{agentId}/architecture", s.handleGetArchitecture).Methods("GET")
	api.HandleFunc("/agents/{agentId}/execute/{entrypoint}", s.handleRunAgent).Methods("POST")

	return router
}

// Start starts the server
func (s *Server) Start() error {
	log.Printf("🚀 Starting local server on %s", s.server.Addr)
	log.Printf("🆔 Agent ID: %s", s.agentID)
	log.Printf("📁 Agent Path: %s", s.agentPath)

	return s.server.ListenAndServe()
}

// Shutdown gracefully shuts down the server
func (s *Server) Shutdown(ctx context.Context) error {
	log.Println("🛑 Shutting down server...")
	return s.server.Shutdown(ctx)
}

// Address returns the server address
func (s *Server) Address() string {
	return s.server.Addr
}

// handleRoot handles the root endpoint
func (s *Server) handleRoot(w http.ResponseWriter, r *http.Request) {
	info := types.AgentInfo{
		Message: fmt.Sprintf("RunAgent API - Agent %s", s.agentID),
		Version: "0.1.0",
		Host:    s.host,
		Port:    s.port,
		Config: map[string]interface{}{
			"agent_id":   s.agentID,
			"agent_path": s.agentPath,
			"framework":  "langchain",
		},
		Endpoints: map[string]string{
			"GET /":                                "Agent info",
			"GET /health":                          "Health check",
			"GET /api/v1/agents/{id}/architecture": "Agent architecture",
			"POST /api/v1/agents/{id}/execute/{entrypoint}": "Run agent",
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(info)
}

// handleHealth handles health check requests
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	health := types.HealthResponse{
		Status:    "healthy",
		Server:    "RunAgent Local Server",
		Timestamp: time.Now().Format(time.RFC3339),
		Version:   "0.1.0",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(health)
}

// handleGetArchitecture handles agent architecture requests
func (s *Server) handleGetArchitecture(w http.ResponseWriter, r *http.Request) {
	architecture := types.AgentArchitecture{
		Entrypoints: []types.EntryPoint{
			{
				File:   "main.py",
				Module: "run",
				Tag:    "generic",
			},
			{
				File:   "main.py",
				Module: "run_stream",
				Tag:    "generic_stream",
			},
			{
				File:   "main.py",
				Module: "health_check",
				Tag:    "health",
			},
		},
	}

	response := map[string]interface{}{
		"agent_id":    s.agentID,
		"framework":   "langchain",
		"entrypoints": architecture.Entrypoints,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleRunAgent handles agent execution requests
func (s *Server) handleRunAgent(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	entrypoint := vars["entrypoint"]

	var request types.AgentRunRequest
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, fmt.Sprintf("Invalid request body: %v", err), http.StatusBadRequest)
		return
	}

	startTime := time.Now()

	// Mock execution based on entrypoint
	var success bool
	var outputData interface{}
	var errorMsg string

	switch entrypoint {
	case "generic":
		success, outputData, errorMsg = s.executeGeneric(request.InputData)
	case "health":
		success, outputData, errorMsg = s.executeHealth()
	default:
		success = false
		errorMsg = fmt.Sprintf("Unknown entrypoint: %s", entrypoint)
	}

	executionTime := time.Since(startTime).Seconds()

	response := types.AgentRunResponse{
		Success:       success,
		OutputData:    outputData,
		Error:         errorMsg,
		ExecutionTime: executionTime,
		AgentID:       s.agentID,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// executeGeneric executes the generic entrypoint
func (s *Server) executeGeneric(input types.AgentInputArgs) (bool, interface{}, string) {
	// Extract message from kwargs or args
	message := "Hello from RunAgent!"
	if msg, ok := input.InputKwargs["message"].(string); ok {
		message = msg
	} else if len(input.InputArgs) > 0 {
		if msg, ok := input.InputArgs[0].(string); ok {
			message = msg
		}
	}

	temperature := 0.7
	if temp, ok := input.InputKwargs["temperature"].(float64); ok {
		temperature = temp
	}

	model := "gpt-3.5-turbo"
	if m, ok := input.InputKwargs["model"].(string); ok {
		model = m
	}

	output := map[string]interface{}{
		"success":  true,
		"response": fmt.Sprintf("Mock LangChain response to: %s", message),
		"input": map[string]interface{}{
			"message":     message,
			"temperature": temperature,
			"model":       model,
		},
		"metadata": map[string]interface{}{
			"timestamp":       time.Now().Format(time.RFC3339),
			"framework":       "langchain",
			"agent_type":      "test_mock",
			"model_used":      model,
			"response_length": len(message) + 25,
			"mock":            true,
		},
	}

	return true, output, ""
}

// executeHealth executes the health entrypoint
func (s *Server) executeHealth() (bool, interface{}, string) {
	output := map[string]interface{}{
		"status":     "healthy",
		"framework":  "langchain",
		"agent_type": "test",
		"timestamp":  time.Now().Format(time.RFC3339),
		"environment": map[string]interface{}{
			"server":  "go",
			"version": "0.1.0",
		},
	}

	return true, output, ""
}
