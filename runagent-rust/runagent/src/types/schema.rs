//! Schema types for the RunAgent SDK
//! 
//! These types mirror the Python SDK's Pydantic models

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
// use uuid::Uuid;

/// Template source configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateSource {
    /// GitHub repository URL
    pub repo_url: String,
    /// Template author name
    pub author: String,
    /// Path to template in repository
    pub path: String,
}

/// Entrypoint configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntryPoint {
    /// Entrypoint file
    pub file: String,
    /// Entrypoint module name
    pub module: String,
    /// Entrypoint tag
    pub tag: String,
}

/// Agent architecture configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentArchitecture {
    /// List of entrypoints
    pub entrypoints: Vec<EntryPoint>,
}

/// RunAgent configuration schema
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunAgentConfig {
    /// Name of the agent
    pub agent_name: String,
    /// Description of the agent
    pub description: String,
    /// Framework used (langchain, etc)
    pub framework: String,
    /// Template name
    pub template: String,
    /// Agent version
    pub version: String,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Template source details
    pub template_source: Option<TemplateSource>,
    /// Agent architecture details
    pub agent_architecture: AgentArchitecture,
    /// Environment variables
    #[serde(default)]
    pub env_vars: HashMap<String, String>,
}

/// Input arguments for agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentInputArgs {
    /// Input arguments list
    #[serde(default)]
    pub input_args: Vec<serde_json::Value>,
    /// Input keyword arguments
    #[serde(default)]
    pub input_kwargs: HashMap<String, serde_json::Value>,
}

impl Default for AgentInputArgs {
    fn default() -> Self {
        Self {
            input_args: Vec::new(),
            input_kwargs: HashMap::new(),
        }
    }
}

/// WebSocket action types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WebSocketActionType {
    StartStream,
    StopStream,
    Ping,
}

/// WebSocket request for agent streaming
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebSocketAgentRequest {
    pub action: WebSocketActionType,
    pub agent_id: String,
    pub entrypoint_tag: String,
    pub input_data: AgentInputArgs,
    #[serde(default)]
    pub stream_config: HashMap<String, serde_json::Value>,
}

/// Request model for agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRunRequest {
    /// Input data for agent invocation
    #[serde(default)]
    pub input_data: AgentInputArgs,
}

/// Response model for agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRunResponse {
    pub success: bool,
    pub output_data: Option<serde_json::Value>,
    pub error: Option<String>,
    pub execution_time: Option<f64>,
    pub agent_id: String,
}

/// Database capacity information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapacityInfo {
    pub current_count: usize,
    pub max_capacity: usize,
    pub remaining_slots: usize,
    pub is_full: bool,
    pub agents: Vec<HashMap<String, serde_json::Value>>,
}

/// Agent information and endpoints
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentInfo {
    pub message: String,
    pub version: String,
    pub host: String,
    pub port: u16,
    pub config: HashMap<String, serde_json::Value>,
    pub endpoints: HashMap<String, String>,
}

/// Message types for different framework responses
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MessageType {
    ToolCall,
    ToolResult,
    AgentThought,
    FinalResponse,
    Error,
    ExecutionError,
    Status,
    RawData,
    Data,
    StructuredData,
}

/// Safe message wrapper for WebSocket communication
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafeMessage {
    pub id: String,
    #[serde(rename = "type")]
    pub message_type: MessageType,
    pub timestamp: String,
    pub data: serde_json::Value,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
    pub error: Option<String>,
}

impl SafeMessage {
    pub fn new(
        id: String,
        message_type: MessageType,
        data: serde_json::Value,
    ) -> Self {
        Self {
            id,
            message_type,
            timestamp: Utc::now().to_rfc3339(),
            data,
            metadata: None,
            error: None,
        }
    }

    pub fn with_error(id: String, error: String) -> Self {
        Self {
            id,
            message_type: MessageType::Error,
            timestamp: Utc::now().to_rfc3339(),
            data: serde_json::json!({"error": error}),
            metadata: None,
            error: Some(error),
        }
    }

    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut dict = HashMap::new();
        dict.insert("id".to_string(), serde_json::json!(self.id));
        dict.insert("type".to_string(), serde_json::json!(self.message_type));
        dict.insert("timestamp".to_string(), serde_json::json!(self.timestamp));
        dict.insert("data".to_string(), self.data.clone());
        
        if let Some(metadata) = &self.metadata {
            dict.insert("metadata".to_string(), serde_json::json!(metadata));
        }
        
        if let Some(error) = &self.error {
            dict.insert("error".to_string(), serde_json::json!(error));
        }
        
        dict
    }
}

/// Agent deployment information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentDeployment {
    pub agent_id: String,
    pub agent_path: String,
    pub host: String,
    pub port: u16,
    pub framework: String,
    pub status: String,
    pub deployed_at: DateTime<Utc>,
    pub last_run: Option<DateTime<Utc>>,
    pub run_count: i64,
    pub success_count: i64,
    pub error_count: i64,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Agent run record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentRun {
    pub id: i64,
    pub agent_id: String,
    pub input_data: serde_json::Value,
    pub output_data: Option<serde_json::Value>,
    pub success: bool,
    pub error_message: Option<String>,
    pub execution_time: Option<f64>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

/// Configuration for local server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub debug: bool,
    pub cors_enabled: bool,
    pub max_request_size: usize,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),
            port: 8450,
            debug: false,
            cors_enabled: true,
            max_request_size: 16 * 1024 * 1024, // 16MB
        }
    }
}

/// Database configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub url: String,
    pub max_connections: u32,
    pub min_connections: u32,
    pub connect_timeout: u64,
    pub idle_timeout: u64,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        // Use default path for database
        let db_path = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".runagent")
            .join("runagent_local.db");
        Self {
            url: format!("sqlite://{}", db_path.to_string_lossy()),
            max_connections: 10,
            min_connections: 1,
            connect_timeout: 30,
            idle_timeout: 600,
        }
    }
}

/// Client configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientConfig {
    pub api_key: Option<String>,
    pub base_url: String,
    pub timeout: u64,
    pub max_retries: usize,
    pub retry_delay: u64,
}

impl Default for ClientConfig {
    fn default() -> Self {
        Self {
            api_key: None,
            base_url: crate::constants::DEFAULT_BASE_URL.to_string(),
            timeout: 30,
            max_retries: 3,
            retry_delay: 1000,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_input_args_default() {
        let args = AgentInputArgs::default();
        assert!(args.input_args.is_empty());
        assert!(args.input_kwargs.is_empty());
    }

    #[test]
    fn test_safe_message_creation() {
        let msg = SafeMessage::new(
            "test-id".to_string(),
            MessageType::Status,
            serde_json::json!({"status": "ok"}),
        );
        assert_eq!(msg.id, "test-id");
        assert!(matches!(msg.message_type, MessageType::Status));
    }

    #[test]
    fn test_safe_message_with_error() {
        let msg = SafeMessage::with_error("error-id".to_string(), "Something went wrong".to_string());
        assert_eq!(msg.id, "error-id");
        assert!(matches!(msg.message_type, MessageType::Error));
        assert!(msg.error.is_some());
    }

    #[test]
    fn test_server_config_default() {
        let config = ServerConfig::default();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 8450);
        assert!(!config.debug);
        assert!(config.cors_enabled);
    }

    #[test]
    fn test_serialization() {
        let entry_point = EntryPoint {
            file: "main.py".to_string(),
            module: "run".to_string(),
            tag: "generic".to_string(),
        };

        let json = serde_json::to_string(&entry_point).unwrap();
        let deserialized: EntryPoint = serde_json::from_str(&json).unwrap();
        
        assert_eq!(entry_point.file, deserialized.file);
        assert_eq!(entry_point.module, deserialized.module);
        assert_eq!(entry_point.tag, deserialized.tag);
    }
}