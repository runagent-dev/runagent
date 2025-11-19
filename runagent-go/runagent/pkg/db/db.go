package db

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/constants"
)

// Agent represents an agent in the database
type Agent struct {
	AgentID      string     `json:"agent_id"`
	AgentPath    string     `json:"agent_path"`
	Host         string     `json:"host"`
	Port         int        `json:"port"`
	Framework    string     `json:"framework"`
	Status       string     `json:"status"`
	DeployedAt   time.Time  `json:"deployed_at"`
	LastRun      *time.Time `json:"last_run,omitempty"`
	RunCount     int64      `json:"run_count"`
	SuccessCount int64      `json:"success_count"`
	ErrorCount   int64      `json:"error_count"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
}

// AgentRun represents an agent execution record
type AgentRun struct {
	ID            int64      `json:"id"`
	AgentID       string     `json:"agent_id"`
	InputData     string     `json:"input_data"`
	OutputData    *string    `json:"output_data,omitempty"`
	Success       bool       `json:"success"`
	ErrorMessage  *string    `json:"error_message,omitempty"`
	ExecutionTime *float64   `json:"execution_time,omitempty"`
	StartedAt     time.Time  `json:"started_at"`
	CompletedAt   *time.Time `json:"completed_at,omitempty"`
}

// AddAgentResult represents the result of adding an agent
type AddAgentResult struct {
	Success           bool   `json:"success"`
	Message           string `json:"message"`
	CurrentCount      int    `json:"current_count"`
	LimitSource       string `json:"limit_source"`
	APICheckPerformed bool   `json:"api_check_performed"`
	AllocatedHost     string `json:"allocated_host,omitempty"`
	AllocatedPort     int    `json:"allocated_port,omitempty"`
	Address           string `json:"address,omitempty"`
	Error             string `json:"error,omitempty"`
	Code              string `json:"code,omitempty"`
}

// CapacityInfo represents database capacity information
type CapacityInfo struct {
	CurrentCount   int                      `json:"current_count"`
	MaxCapacity    int                      `json:"max_capacity"`
	DefaultLimit   int                      `json:"default_limit"`
	RemainingSlots *int                     `json:"remaining_slots,omitempty"`
	IsFull         bool                     `json:"is_full"`
	Agents         []map[string]interface{} `json:"agents"`
}

// Service provides database operations
type Service struct {
	db *sql.DB
}

// NewService creates a new database service
func NewService(dbPath string) (*Service, error) {
	if dbPath == "" {
		dbPath = constants.GetDatabasePath()
	}

	// Create directory if it doesn't exist
	if err := os.MkdirAll(filepath.Dir(dbPath), 0755); err != nil {
		return nil, fmt.Errorf("failed to create database directory: %w", err)
	}

	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	service := &Service{db: db}

	if err := service.createTables(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create tables: %w", err)
	}

	return service, nil
}

// Close closes the database connection
func (s *Service) Close() error {
	return s.db.Close()
}

// createTables creates the necessary database tables
func (s *Service) createTables() error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS agents (
			agent_id TEXT PRIMARY KEY,
			agent_path TEXT NOT NULL,
			host TEXT NOT NULL DEFAULT 'localhost',
			port INTEGER NOT NULL DEFAULT 8450,
			framework TEXT,
			status TEXT NOT NULL DEFAULT 'deployed',
			deployed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			last_run DATETIME,
			run_count INTEGER NOT NULL DEFAULT 0,
			success_count INTEGER NOT NULL DEFAULT 0,
			error_count INTEGER NOT NULL DEFAULT 0,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS agent_runs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			agent_id TEXT NOT NULL,
			input_data TEXT NOT NULL,
			output_data TEXT,
			success BOOLEAN NOT NULL,
			error_message TEXT,
			execution_time REAL,
			started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			completed_at DATETIME,
			FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
		)`,
		`CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)`,
		`CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs(agent_id)`,
		`CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs(started_at)`,
	}

	for _, query := range queries {
		if _, err := s.db.Exec(query); err != nil {
			return fmt.Errorf("failed to execute query: %w", err)
		}
	}

	return nil
}

// AddAgent adds a new agent to the database
func (s *Service) AddAgent(agent *Agent) (*AddAgentResult, error) {
	// Check current count
	currentCount, err := s.getAgentCount()
	if err != nil {
		return nil, err
	}

	// Check if we're within limits
	defaultLimit := constants.MaxLocalAgents
	if currentCount >= defaultLimit {
		return &AddAgentResult{
			Success:      false,
			Error:        fmt.Sprintf("Maximum %d agents allowed", defaultLimit),
			Code:         "DATABASE_FULL",
			CurrentCount: currentCount,
		}, nil
	}

	// Set defaults
	now := time.Now()
	if agent.DeployedAt.IsZero() {
		agent.DeployedAt = now
	}
	if agent.CreatedAt.IsZero() {
		agent.CreatedAt = now
	}
	if agent.UpdatedAt.IsZero() {
		agent.UpdatedAt = now
	}
	if agent.Status == "" {
		agent.Status = "deployed"
	}
	if agent.Host == "" {
		agent.Host = "localhost"
	}
	if agent.Port == 0 {
		agent.Port = 8450
	}

	// Insert agent
	query := `INSERT INTO agents (
		agent_id, agent_path, host, port, framework, status,
		deployed_at, created_at, updated_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`

	_, err = s.db.Exec(query,
		agent.AgentID, agent.AgentPath, agent.Host, agent.Port,
		agent.Framework, agent.Status, agent.DeployedAt,
		agent.CreatedAt, agent.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to insert agent: %w", err)
	}

	return &AddAgentResult{
		Success:           true,
		Message:           fmt.Sprintf("Agent %s added successfully", agent.AgentID),
		CurrentCount:      currentCount + 1,
		LimitSource:       "default",
		APICheckPerformed: false,
		AllocatedHost:     agent.Host,
		AllocatedPort:     agent.Port,
		Address:           fmt.Sprintf("%s:%d", agent.Host, agent.Port),
	}, nil
}

// GetAgent retrieves an agent by ID
func (s *Service) GetAgent(agentID string) (*Agent, error) {
	query := `SELECT agent_id, agent_path, host, port, framework, status,
		deployed_at, last_run, run_count, success_count, error_count,
		created_at, updated_at FROM agents WHERE agent_id = ?`

	var agent Agent
	var lastRun sql.NullTime

	err := s.db.QueryRow(query, agentID).Scan(
		&agent.AgentID, &agent.AgentPath, &agent.Host, &agent.Port,
		&agent.Framework, &agent.Status, &agent.DeployedAt, &lastRun,
		&agent.RunCount, &agent.SuccessCount, &agent.ErrorCount,
		&agent.CreatedAt, &agent.UpdatedAt,
	)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get agent: %w", err)
	}

	if lastRun.Valid {
		agent.LastRun = &lastRun.Time
	}

	return &agent, nil
}

// ListAgents returns all agents
func (s *Service) ListAgents() ([]*Agent, error) {
	query := `SELECT agent_id, agent_path, host, port, framework, status,
		deployed_at, last_run, run_count, success_count, error_count,
		created_at, updated_at FROM agents ORDER BY deployed_at DESC`

	rows, err := s.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query agents: %w", err)
	}
	defer rows.Close()

	var agents []*Agent
	for rows.Next() {
		var agent Agent
		var lastRun sql.NullTime

		err := rows.Scan(
			&agent.AgentID, &agent.AgentPath, &agent.Host, &agent.Port,
			&agent.Framework, &agent.Status, &agent.DeployedAt, &lastRun,
			&agent.RunCount, &agent.SuccessCount, &agent.ErrorCount,
			&agent.CreatedAt, &agent.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan agent: %w", err)
		}

		if lastRun.Valid {
			agent.LastRun = &lastRun.Time
		}

		agents = append(agents, &agent)
	}

	return agents, nil
}

// GetCapacityInfo returns database capacity information
func (s *Service) GetCapacityInfo() (*CapacityInfo, error) {
	currentCount, err := s.getAgentCount()
	if err != nil {
		return nil, err
	}

	agents, err := s.ListAgents()
	if err != nil {
		return nil, err
	}

	agentMaps := make([]map[string]interface{}, len(agents))
	for i, agent := range agents {
		agentMaps[i] = map[string]interface{}{
			"agent_id":    agent.AgentID,
			"host":        agent.Host,
			"port":        agent.Port,
			"framework":   agent.Framework,
			"status":      agent.Status,
			"deployed_at": agent.DeployedAt,
		}
	}

	defaultLimit := constants.MaxLocalAgents
	remaining := defaultLimit - currentCount
	if remaining < 0 {
		remaining = 0
	}

	return &CapacityInfo{
		CurrentCount:   currentCount,
		MaxCapacity:    defaultLimit,
		DefaultLimit:   defaultLimit,
		RemainingSlots: &remaining,
		IsFull:         currentCount >= defaultLimit,
		Agents:         agentMaps,
	}, nil
}

// getAgentCount returns the current number of agents
func (s *Service) getAgentCount() (int, error) {
	var count int
	err := s.db.QueryRow("SELECT COUNT(*) FROM agents").Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("failed to count agents: %w", err)
	}
	return count, nil
}

// RecordAgentRun records an agent execution
func (s *Service) RecordAgentRun(run *AgentRun) error {
	query := `INSERT INTO agent_runs (
		agent_id, input_data, output_data, success, error_message,
		execution_time, started_at, completed_at
	) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`

	_, err := s.db.Exec(query,
		run.AgentID, run.InputData, run.OutputData, run.Success,
		run.ErrorMessage, run.ExecutionTime, run.StartedAt, run.CompletedAt,
	)
	if err != nil {
		return fmt.Errorf("failed to record agent run: %w", err)
	}

	// Update agent statistics
	updateQuery := `UPDATE agents SET 
		run_count = run_count + 1,
		success_count = CASE WHEN ? THEN success_count + 1 ELSE success_count END,
		error_count = CASE WHEN ? THEN error_count ELSE error_count + 1 END,
		last_run = ?,
		updated_at = ?
		WHERE agent_id = ?`

	_, err = s.db.Exec(updateQuery, run.Success, run.Success,
		run.StartedAt, time.Now(), run.AgentID)
	if err != nil {
		return fmt.Errorf("failed to update agent stats: %w", err)
	}

	return nil
}
