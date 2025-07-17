package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/runagent-dev/runagent/runagent-go/runagent/pkg/constants"
)

// Config holds the SDK configuration
type Config struct {
	APIKey   string                 `json:"api_key,omitempty"`
	BaseURL  string                 `json:"base_url"`
	UserInfo map[string]interface{} `json:"user_info"`
}

// Load loads configuration from various sources
func Load() (*Config, error) {
	config := &Config{
		BaseURL:  constants.DefaultBaseURL,
		UserInfo: make(map[string]interface{}),
	}

	// Load from file
	if err := config.loadFromFile(); err != nil {
		// File doesn't exist or is invalid, continue with defaults
	}

	// Override with environment variables
	if apiKey := os.Getenv(constants.EnvAPIKey); apiKey != "" {
		config.APIKey = apiKey
	}

	if baseURL := os.Getenv(constants.EnvBaseURL); baseURL != "" {
		config.BaseURL = baseURL
	}

	// Ensure proper URL format
	if !strings.HasPrefix(config.BaseURL, "http://") && !strings.HasPrefix(config.BaseURL, "https://") {
		config.BaseURL = "https://" + config.BaseURL
	}

	return config, nil
}

// loadFromFile loads configuration from the config file
func (c *Config) loadFromFile() error {
	configPath := c.getConfigFilePath()
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return nil // File doesn't exist, use defaults
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		return fmt.Errorf("failed to read config file: %w", err)
	}

	if err := json.Unmarshal(data, c); err != nil {
		return fmt.Errorf("failed to parse config file: %w", err)
	}

	return nil
}

// Save saves the configuration to file
func (c *Config) Save() error {
	configPath := c.getConfigFilePath()

	// Create directory if it doesn't exist
	if err := os.MkdirAll(filepath.Dir(configPath), 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to serialize config: %w", err)
	}

	if err := os.WriteFile(configPath, data, 0600); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}

// SetAPIKey sets the API key
func (c *Config) SetAPIKey(apiKey string) {
	c.APIKey = apiKey
}

// SetBaseURL sets the base URL
func (c *Config) SetBaseURL(baseURL string) {
	if !strings.HasPrefix(baseURL, "http://") && !strings.HasPrefix(baseURL, "https://") {
		baseURL = "https://" + baseURL
	}
	c.BaseURL = baseURL
}

// IsConfigured checks if the SDK is properly configured
func (c *Config) IsConfigured() bool {
	return c.APIKey != "" && c.BaseURL != ""
}

// GetStatus returns the configuration status
func (c *Config) GetStatus() map[string]interface{} {
	return map[string]interface{}{
		"configured":    c.IsConfigured(),
		"api_key_set":   c.APIKey != "",
		"base_url":      c.BaseURL,
		"user_info":     c.UserInfo,
		"config_file":   c.getConfigFilePath(),
		"config_exists": c.configFileExists(),
	}
}

// getConfigFilePath returns the path to the config file
func (c *Config) getConfigFilePath() string {
	return filepath.Join(constants.GetLocalCacheDirectory(), constants.UserDataFileName)
}

// configFileExists checks if the config file exists
func (c *Config) configFileExists() bool {
	_, err := os.Stat(c.getConfigFilePath())
	return err == nil
}

// Clear removes the configuration file
func Clear() error {
	config := &Config{}
	configPath := config.getConfigFilePath()

	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return nil // File doesn't exist
	}

	return os.Remove(configPath)
}
