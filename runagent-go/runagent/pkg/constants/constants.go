package constants

import (
	"os"
	"path/filepath"
)

const (
	// Template repository configuration
	TemplateRepoURL  = "https://github.com/runagent-dev/runagent.git"
	TemplateBranch   = "main"
	TemplatePrePath  = "templates"
	DefaultFramework = "langchain"
	DefaultTemplate  = "basic"

	// Environment variables
	EnvAPIKey   = "RUNAGENT_API_KEY"
	EnvBaseURL  = "RUNAGENT_BASE_URL"
	EnvCacheDir = "RUNAGENT_CACHE_DIR"
	EnvLogLevel = "RUNAGENT_LOGGING_LEVEL"

	// Default values
	DefaultBaseURL      = "http://52.237.88.147:8330/"
	AgentConfigFileName = "runagent.config.json"
	UserDataFileName    = "user_data.json"
	DatabaseFileName    = "runagent_local.db"

	// Port configuration
	DefaultPortStart = 8450
	DefaultPortEnd   = 8500

	// Limits
	MaxLocalAgents = 5
)

// GetLocalCacheDirectory returns the local cache directory path
func GetLocalCacheDirectory() string {
	if envPath := os.Getenv(EnvCacheDir); envPath != "" {
		return envPath
	}

	homeDir, err := os.UserHomeDir()
	if err != nil {
		return ".runagent"
	}

	return filepath.Join(homeDir, ".runagent")
}

// GetDatabasePath returns the full path to the database file
func GetDatabasePath() string {
	return filepath.Join(GetLocalCacheDirectory(), DatabaseFileName)
}

// Framework represents supported AI frameworks
type Framework string

const (
	FrameworkLangGraph  Framework = "langgraph"
	FrameworkLangChain  Framework = "langchain"
	FrameworkLlamaIndex Framework = "llamaindex"
	FrameworkCrewAI     Framework = "crewai"
	FrameworkAutoGen    Framework = "autogen"
	FrameworkDefault    Framework = "default"
)

// String returns the string representation of the framework
func (f Framework) String() string {
	return string(f)
}

// IsValid checks if the framework is supported
func (f Framework) IsValid() bool {
	switch f {
	case FrameworkLangGraph, FrameworkLangChain, FrameworkLlamaIndex,
		FrameworkCrewAI, FrameworkAutoGen, FrameworkDefault:
		return true
	default:
		return false
	}
}
