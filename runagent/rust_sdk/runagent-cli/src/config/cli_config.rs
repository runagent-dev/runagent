//! CLI-specific configuration structure
//!
//! Extends the base SDK configuration with CLI-specific settings
//! like output preferences, default values, and user preferences.

use anyhow::Result;
use runagent::utils::Config as SdkConfig;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

/// CLI-specific configuration that extends the SDK config
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CliConfig {
    /// Base SDK configuration
    #[serde(flatten)]
    pub sdk: SdkConfig,
    
    /// CLI-specific settings
    pub cli: CliSettings,
}

/// CLI-specific settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CliSettings {
    /// Default output format (json, table, yaml)
    pub default_output_format: String,
    
    /// Enable colored output by default
    pub colored_output: bool,
    
    /// Show verbose output by default
    pub verbose: bool,
    
    /// Default framework for init command
    pub default_framework: String,
    
    /// Default template for init command
    pub default_template: String,
    
    /// Default host for serve command
    pub default_host: String,
    
    /// Default port range for auto-allocation
    pub default_port_range: (u16, u16),
    
    /// Auto-confirm operations (dangerous!)
    pub auto_confirm: bool,
    
    /// User preferences
    pub user_preferences: HashMap<String, serde_json::Value>,
}

impl Default for CliSettings {
    fn default() -> Self {
        Self {
            default_output_format: "table".to_string(),
            colored_output: true,
            verbose: false,
            default_framework: "langchain".to_string(),
            default_template: "basic".to_string(),
            default_host: "127.0.0.1".to_string(),
            default_port_range: (8450, 8500),
            auto_confirm: false,
            user_preferences: HashMap::new(),
        }
    }
}

impl Default for CliConfig {
    fn default() -> Self {
        Self {
            sdk: SdkConfig::default(),
            cli: CliSettings::default(),
        }
    }
}

impl CliConfig {
    /// Load CLI configuration from various sources
    pub fn load() -> Result<Self> {
        // Load base SDK config
        let sdk_config = SdkConfig::load()?;
        
        // Load CLI-specific settings (would be from a separate file)
        let cli_settings = CliSettings::default(); // For now, use defaults
        
        Ok(Self {
            sdk: sdk_config,
            cli: cli_settings,
        })
    }
    
    /// Save CLI configuration
    pub fn save(&self) -> Result<()> {
        // Save SDK config
        self.sdk.save()?;
        
        // TODO: Save CLI-specific settings to separate file
        // This would save to ~/.runagent/cli_config.json or similar
        
        Ok(())
    }
    
    /// Check if CLI is properly configured
    pub fn is_configured(&self) -> bool {
        self.sdk.is_configured()
    }
    
    /// Get user preference value
    pub fn get_preference(&self, key: &str) -> Option<&serde_json::Value> {
        self.cli.user_preferences.get(key)
    }
    
    /// Set user preference value
    pub fn set_preference(&mut self, key: String, value: serde_json::Value) {
        self.cli.user_preferences.insert(key, value);
    }
    
    /// Get default project path for init commands
    pub fn get_default_project_path(&self) -> PathBuf {
        std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
    }
    
    /// Check if colored output should be used
    pub fn use_colored_output(&self) -> bool {
        // Check environment variable first
        if let Ok(no_color) = std::env::var("NO_COLOR") {
            return no_color.is_empty();
        }
        
        // Fall back to config setting
        self.cli.colored_output
    }
    
    /// Get the appropriate framework for a project type
    pub fn get_framework_for_type(&self, project_type: &str) -> String {
        match project_type {
            "python" => "langchain".to_string(),
            "rust" => "rust-langchain".to_string(),
            "javascript" | "typescript" => "langchain-js".to_string(),
            _ => self.cli.default_framework.clone(),
        }
    }
    
    /// Update CLI settings
    pub fn update_cli_settings<F>(&mut self, updater: F) -> Result<()>
    where
        F: FnOnce(&mut CliSettings),
    {
        updater(&mut self.cli);
        self.save()
    }
}

/// CLI configuration builder for easier setup
pub struct CliConfigBuilder {
    config: CliConfig,
}

impl CliConfigBuilder {
    /// Create a new config builder
    pub fn new() -> Self {
        Self {
            config: CliConfig::default(),
        }
    }
    
    /// Set API key
    pub fn with_api_key(mut self, api_key: String) -> Self {
        self.config.sdk.api_key = Some(api_key);
        self
    }
    
    /// Set base URL
    pub fn with_base_url(mut self, base_url: String) -> Self {
        self.config.sdk.base_url = base_url;
        self
    }
    
    /// Set colored output preference
    pub fn with_colored_output(mut self, colored: bool) -> Self {
        self.config.cli.colored_output = colored;
        self
    }
    
    /// Set verbose output preference
    pub fn with_verbose(mut self, verbose: bool) -> Self {
        self.config.cli.verbose = verbose;
        self
    }
    
    /// Set default framework
    pub fn with_default_framework(mut self, framework: String) -> Self {
        self.config.cli.default_framework = framework;
        self
    }
    
    /// Build the configuration
    pub fn build(self) -> CliConfig {
        self.config
    }
}

impl Default for CliConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cli_config_default() {
        let config = CliConfig::default();
        assert!(config.cli.colored_output);
        assert!(!config.cli.verbose);
        assert_eq!(config.cli.default_framework, "langchain");
        assert_eq!(config.cli.default_host, "127.0.0.1");
    }

    #[test]
    fn test_cli_config_builder() {
        let config = CliConfigBuilder::new()
            .with_api_key("test-key".to_string())
            .with_colored_output(false)
            .with_verbose(true)
            .with_default_framework("rust-langchain".to_string())
            .build();

        assert_eq!(config.sdk.api_key, Some("test-key".to_string()));
        assert!(!config.cli.colored_output);
        assert!(config.cli.verbose);
        assert_eq!(config.cli.default_framework, "rust-langchain");
    }

    #[test]
    fn test_framework_for_type() {
        let config = CliConfig::default();
        assert_eq!(config.get_framework_for_type("python"), "langchain");
        assert_eq!(config.get_framework_for_type("rust"), "rust-langchain");
        assert_eq!(config.get_framework_for_type("unknown"), "langchain");
    }

    #[test]
    fn test_user_preferences() {
        let mut config = CliConfig::default();
        
        config.set_preference(
            "favorite_model".to_string(), 
            serde_json::json!("gpt-4")
        );
        
        assert_eq!(
            config.get_preference("favorite_model"),
            Some(&serde_json::json!("gpt-4"))
        );
        
        assert_eq!(config.get_preference("nonexistent"), None);
    }

    #[test]
    fn test_colored_output_env_override() {
        // Test that NO_COLOR environment variable overrides config
        std::env::set_var("NO_COLOR", "1");
        let config = CliConfig::default();
        assert!(!config.use_colored_output());
        
        std::env::set_var("NO_COLOR", "");
        assert!(config.use_colored_output());
        
        std::env::remove_var("NO_COLOR");
    }
}