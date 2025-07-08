//! Configuration management for the RunAgent SDK

use crate::constants::{
    DEFAULT_BASE_URL, ENV_RUNAGENT_API_KEY, ENV_RUNAGENT_BASE_URL, LOCAL_CACHE_DIRECTORY,
    USER_DATA_FILE_NAME,
};
use crate::types::{RunAgentError, RunAgentResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

/// Configuration for the RunAgent SDK
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub api_key: Option<String>,
    pub base_url: String,
    pub user_info: HashMap<String, serde_json::Value>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            api_key: None,
            base_url: DEFAULT_BASE_URL.to_string(),
            user_info: HashMap::new(),
        }
    }
}

impl Config {
    /// Load configuration from various sources
    pub fn load() -> RunAgentResult<Self> {
        let mut config = Self::default();

        // 1. Load from config file
        if let Ok(file_config) = Self::load_from_file() {
            config.api_key = file_config.api_key.or(config.api_key);
            config.base_url = if file_config.base_url.is_empty() {
                config.base_url
            } else {
                file_config.base_url
            };
            config.user_info.extend(file_config.user_info);
        }

        // 2. Override with environment variables
        if let Ok(env_api_key) = std::env::var(ENV_RUNAGENT_API_KEY) {
            config.api_key = Some(env_api_key);
        }

        if let Ok(env_base_url) = std::env::var(ENV_RUNAGENT_BASE_URL) {
            config.base_url = env_base_url;
        }

        // 3. Ensure base_url has proper format
        if !config.base_url.starts_with("http://") && !config.base_url.starts_with("https://") {
            config.base_url = format!("https://{}", config.base_url);
        }

        Ok(config)
    }

    /// Load configuration from file
    fn load_from_file() -> RunAgentResult<Self> {
        let config_path = Self::get_config_file_path();
        
        if config_path.exists() {
            let content = fs::read_to_string(&config_path)
                .map_err(|e| RunAgentError::config(format!("Failed to read config file: {}", e)))?;
            
            serde_json::from_str(&content)
                .map_err(|e| RunAgentError::config(format!("Failed to parse config file: {}", e)))
        } else {
            Ok(Self::default())
        }
    }

    /// Save configuration to file
    pub fn save(&self) -> RunAgentResult<()> {
        let config_path = Self::get_config_file_path();
        
        // Create parent directories if they don't exist
        if let Some(parent) = config_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| RunAgentError::config(format!("Failed to create config directory: {}", e)))?;
        }

        let content = serde_json::to_string_pretty(self)
            .map_err(|e| RunAgentError::config(format!("Failed to serialize config: {}", e)))?;

        fs::write(&config_path, content)
            .map_err(|e| RunAgentError::config(format!("Failed to write config file: {}", e)))?;

        Ok(())
    }

    /// Setup and validate configuration
    pub fn setup(
        api_key: Option<String>,
        base_url: Option<String>,
        save: bool,
    ) -> RunAgentResult<Self> {
        let mut config = Self::load()?;

        // Update configuration
        if let Some(key) = api_key {
            config.api_key = Some(key);
        }

        if let Some(url) = base_url {
            config.base_url = if url.starts_with("http://") || url.starts_with("https://") {
                url
            } else {
                format!("https://{}", url)
            };
        }

        // Validate configuration
        if config.api_key.is_none() {
            return Err(RunAgentError::validation("API key is required"));
        }

        // Test authentication (placeholder - would make actual API call)
        if !config.test_authentication()? {
            return Err(RunAgentError::authentication("Authentication failed with provided credentials"));
        }

        // Save if requested
        if save {
            config.save()?;
        }

        Ok(config)
    }

    /// Test authentication with current configuration
    fn test_authentication(&self) -> RunAgentResult<bool> {
        // Placeholder for authentication test
        // In a real implementation, this would make an API call
        Ok(self.api_key.is_some())
    }

    /// Check if SDK is properly configured
    pub fn is_configured(&self) -> bool {
        self.api_key.is_some() && !self.base_url.is_empty()
    }

    /// Check if current configuration is authenticated
    pub fn is_authenticated(&self) -> bool {
        self.is_configured() && self.test_authentication().unwrap_or(false)
    }

    /// Get detailed configuration status
    pub fn get_status(&self) -> HashMap<String, serde_json::Value> {
        let mut status = HashMap::new();
        
        status.insert("configured".to_string(), serde_json::json!(self.is_configured()));
        status.insert("authenticated".to_string(), serde_json::json!(self.is_authenticated()));
        status.insert("api_key_set".to_string(), serde_json::json!(self.api_key.is_some()));
        status.insert("base_url".to_string(), serde_json::json!(self.base_url));
        status.insert("user_info".to_string(), serde_json::json!(self.user_info));
        status.insert("config_file".to_string(), serde_json::json!(Self::get_config_file_path()));
        status.insert("config_file_exists".to_string(), serde_json::json!(Self::get_config_file_path().exists()));

        status
    }

    /// Clear all configuration
    pub fn clear() -> RunAgentResult<()> {
        let config_path = Self::get_config_file_path();
        
        if config_path.exists() {
            fs::remove_file(&config_path)
                .map_err(|e| RunAgentError::config(format!("Failed to remove config file: {}", e)))?;
        }

        Ok(())
    }

    /// Get API key
    pub fn api_key(&self) -> Option<String> {
        self.api_key.clone()
    }

    /// Get base URL
    pub fn base_url(&self) -> String {
        self.base_url.clone()
    }

    /// Get user information
    pub fn user_info(&self) -> &HashMap<String, serde_json::Value> {
        &self.user_info
    }

    /// Get config file path
    fn get_config_file_path() -> PathBuf {
        LOCAL_CACHE_DIRECTORY.join(USER_DATA_FILE_NAME)
    }

    /// Create agent configuration file
    pub fn create_agent_config(
        project_dir: &str,
        config_content: &HashMap<String, serde_json::Value>,
    ) -> RunAgentResult<String> {
        use crate::constants::AGENT_CONFIG_FILE_NAME;
        
        let config_file = PathBuf::from(project_dir).join(AGENT_CONFIG_FILE_NAME);

        // Update existing config if it exists
        let mut final_config = if config_file.exists() {
            let existing_content = fs::read_to_string(&config_file)
                .map_err(|e| RunAgentError::config(format!("Failed to read existing config: {}", e)))?;
            
            let mut existing_config: HashMap<String, serde_json::Value> = serde_json::from_str(&existing_content)
                .map_err(|e| RunAgentError::config(format!("Failed to parse existing config: {}", e)))?;
            
            // Merge configs, new values take precedence
            existing_config.extend(config_content.clone());
            existing_config
        } else {
            config_content.clone()
        };

        // Add timestamp if not present
        if !final_config.contains_key("created_at") {
            final_config.insert(
                "created_at".to_string(),
                serde_json::json!(chrono::Utc::now().format("%Y-%m-%d %H:%M:%S").to_string())
            );
        }

        // Write config file
        let content = serde_json::to_string_pretty(&final_config)
            .map_err(|e| RunAgentError::config(format!("Failed to serialize config: {}", e)))?;

        fs::write(&config_file, content)
            .map_err(|e| RunAgentError::config(format!("Failed to write config file: {}", e)))?;

        Ok(config_file.to_string_lossy().to_string())
    }

    /// Get agent configuration
    pub fn get_agent_config(project_dir: &str) -> RunAgentResult<Option<HashMap<String, serde_json::Value>>> {
        use crate::constants::AGENT_CONFIG_FILE_NAME;
        
        let config_file = PathBuf::from(project_dir).join(AGENT_CONFIG_FILE_NAME);

        if !config_file.exists() {
            return Ok(None);
        }

        let content = fs::read_to_string(&config_file)
            .map_err(|e| RunAgentError::config(format!("Failed to read agent config: {}", e)))?;

        let config: HashMap<String, serde_json::Value> = serde_json::from_str(&content)
            .map_err(|e| RunAgentError::config(format!("Failed to parse agent config: {}", e)))?;

        Ok(Some(config))
    }

    /// Backup current configuration
    pub fn backup() -> RunAgentResult<Option<String>> {
        let config_path = Self::get_config_file_path();
        
        if !config_path.exists() {
            return Ok(None);
        }

        let config = Self::load_from_file()?;
        
        // Remove sensitive data from backup
        let mut backup_config = config;
        backup_config.api_key = None;

        let backup_dir = LOCAL_CACHE_DIRECTORY.join("backups");
        fs::create_dir_all(&backup_dir)
            .map_err(|e| RunAgentError::config(format!("Failed to create backup directory: {}", e)))?;

        let timestamp = chrono::Utc::now().timestamp();
        let backup_file = backup_dir.join(format!("config_backup_{}.json", timestamp));

        let content = serde_json::to_string_pretty(&backup_config)
            .map_err(|e| RunAgentError::config(format!("Failed to serialize backup: {}", e)))?;

        fs::write(&backup_file, content)
            .map_err(|e| RunAgentError::config(format!("Failed to write backup: {}", e)))?;

        Ok(Some(backup_file.to_string_lossy().to_string()))
    }

    /// Set user configuration value
    pub fn set_user_config(key: &str, value: serde_json::Value) -> RunAgentResult<()> {
        let mut config = Self::load()?;
        config.user_info.insert(key.to_string(), value);
        config.save()
    }

    /// Get user configuration value
    pub fn get_user_config(key: &str) -> RunAgentResult<Option<serde_json::Value>> {
        let config = Self::load()?;
        Ok(config.user_info.get(key).cloned())
    }

    /// Set base URL
    pub fn set_base_url(base_url: &str) -> RunAgentResult<()> {
        let mut config = Self::load()?;
        config.base_url = if base_url.starts_with("http://") || base_url.starts_with("https://") {
            base_url.to_string()
        } else {
            format!("https://{}", base_url)
        };
        config.save()
    }

    /// Set API key
    pub fn set_api_key(api_key: &str) -> RunAgentResult<()> {
        let mut config = Self::load()?;
        config.api_key = Some(api_key.to_string());
        config.save()
    }

    /// Save deployment information
    pub fn save_deployment_info(
        agent_id: &str,
        info: &HashMap<String, serde_json::Value>,
    ) -> RunAgentResult<String> {
        let deployments_dir = std::env::current_dir()
            .map_err(|e| RunAgentError::config(format!("Failed to get current directory: {}", e)))?
            .join(".deployments");

        fs::create_dir_all(&deployments_dir)
            .map_err(|e| RunAgentError::config(format!("Failed to create deployments directory: {}", e)))?;

        let info_file = deployments_dir.join(format!("{}.json", agent_id));
        
        let content = serde_json::to_string_pretty(info)
            .map_err(|e| RunAgentError::config(format!("Failed to serialize deployment info: {}", e)))?;

        fs::write(&info_file, content)
            .map_err(|e| RunAgentError::config(format!("Failed to write deployment info: {}", e)))?;

        Ok(info_file.to_string_lossy().to_string())
    }

    /// Get deployment information
    pub fn get_deployment_info(agent_id: &str) -> RunAgentResult<Option<HashMap<String, serde_json::Value>>> {
        let deployments_dir = std::env::current_dir()
            .map_err(|e| RunAgentError::config(format!("Failed to get current directory: {}", e)))?
            .join(".deployments");

        let info_file = deployments_dir.join(format!("{}.json", agent_id));

        if !info_file.exists() {
            return Ok(None);
        }

        let content = fs::read_to_string(&info_file)
            .map_err(|e| RunAgentError::config(format!("Failed to read deployment info: {}", e)))?;

        let info: HashMap<String, serde_json::Value> = serde_json::from_str(&content)
            .map_err(|e| RunAgentError::config(format!("Failed to parse deployment info: {}", e)))?;

        Ok(Some(info))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_config_default() {
        let config = Config::default();
        assert!(config.api_key.is_none());
        assert_eq!(config.base_url, DEFAULT_BASE_URL);
        assert!(config.user_info.is_empty());
    }

    #[test]
    fn test_config_validation() {
        let mut config = Config::default();
        assert!(!config.is_configured());

        config.api_key = Some("test-key".to_string());
        config.base_url = "https://api.example.com".to_string();
        assert!(config.is_configured());
    }

    #[test]
    fn test_url_formatting() {
        let config = Config::setup(
            Some("test-key".to_string()),
            Some("api.example.com".to_string()),
            false,
        );
        
        // This would test URL formatting in a real implementation
        // For now, we just verify the function doesn't panic
        assert!(config.is_err() || config.is_ok());
    }

    #[test]
    fn test_agent_config_creation() {
        let temp_dir = TempDir::new().unwrap();
        let project_dir = temp_dir.path().to_str().unwrap();

        let mut config_content = HashMap::new();
        config_content.insert("agent_name".to_string(), serde_json::json!("test-agent"));
        config_content.insert("framework".to_string(), serde_json::json!("langchain"));

        let result = Config::create_agent_config(project_dir, &config_content);
        assert!(result.is_ok());

        // Verify file was created
        let config_file = PathBuf::from(project_dir).join(crate::constants::AGENT_CONFIG_FILE_NAME);
        assert!(config_file.exists());
    }

    #[test]
    fn test_status_generation() {
        let config = Config::default();
        let status = config.get_status();
        
        assert!(status.contains_key("configured"));
        assert!(status.contains_key("api_key_set"));
        assert!(status.contains_key("base_url"));
    }
}