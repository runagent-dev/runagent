//! # RunAgent Rust SDK
//!
//! A comprehensive Rust SDK for deploying and managing AI agents with support for multiple
//! frameworks including LangChain, LangGraph, LlamaIndex, and more.
//!
//! ## Features
//!
//! - **Multi-Framework Support**: Built-in support for LangChain, LangGraph, LlamaIndex, Letta, CrewAI, and AutoGen
//! - **Local & Remote Deployment**: Deploy agents locally for testing or to remote servers  
//! - **Real-time Streaming**: WebSocket-based streaming for real-time agent interactions
//! - **Database Management**: SQLite-based storage for agent metadata and execution history
//! - **Template System**: Pre-built templates for quick agent setup
//! - **Type Safety**: Full Rust type safety with comprehensive error handling
//! - **Async/Await**: Built on Tokio for high-performance async operations
//!
//! ## Quick Start
//!
//! ### Basic Agent Interaction
//!
//! ```rust,no_run
//! use runagent::prelude::*;
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Initialize logging
//!     runagent::init_logging();
//!
//!     // Create a client for a local agent
//!     let client = RunAgentClient::new("my-agent-id", "generic", true).await?;
//!     
//!     // Run the agent with input
//!     let response = client.run(&[
//!         ("message", json!("Hello, world!")),
//!         ("temperature", json!(0.7))
//!     ]).await?;
//!     
//!     println!("Response: {}", response);
//!     Ok(())
//! }
//! ```
//!
//! ### Streaming Agent Interaction
//!
//! ```rust,no_run
//! use runagent::prelude::*;
//! use futures::StreamExt;
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = RunAgentClient::new("my-agent-id", "generic_stream", true).await?;
//!     
//!     // Create a streaming connection
//!     let mut stream = client.run_stream(&[
//!         ("message", json!("Tell me a story"))
//!     ]).await?;
//!     
//!     // Process streaming responses
//!     while let Some(chunk) = stream.next().await {
//!         match chunk {
//!             Ok(data) => println!("Chunk: {}", data),
//!             Err(e) => eprintln!("Stream error: {}", e),
//!         }
//!     }
//!     
//!     Ok(())
//! }
//! ```
//!
//! ### Local Server Setup
//!
//! ```rust,no_run
//! use runagent::server::LocalServer;
//! use std::path::PathBuf;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Create a local server for testing
//!     let server = LocalServer::from_path(
//!         PathBuf::from("./my-agent"),
//!         Some("127.0.0.1"),
//!         Some(8450)
//!     ).await?;
//!     
//!     println!("Server info: {:?}", server.get_info());
//!     
//!     // Start the server (this will block)
//!     server.start().await?;
//!     
//!     Ok(())
//! }
//! ```
//!
//! ## Framework-Specific Examples
//!
//! ### LangChain Integration
//!
//! ```rust,no_run
//! use runagent::prelude::*;
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = RunAgentClient::new("langchain-agent", "invoke", true).await?;
//!     
//!     // LangChain invoke pattern
//!     let response = client.run(&[
//!         ("input", json!({
//!             "messages": [
//!                 {"role": "user", "content": "What is the weather like?"}
//!             ]
//!         }))
//!     ]).await?;
//!     
//!     println!("LangChain response: {}", response);
//!     Ok(())
//! }
//! ```
//!
//! ### LangGraph Workflows
//!
//! ```rust,no_run
//! use runagent::prelude::*;
//! use serde_json::json;
//! use futures::StreamExt;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = RunAgentClient::new("langgraph-agent", "stream", true).await?;
//!     
//!     // Stream LangGraph execution
//!     let mut stream = client.run_stream(&[
//!         ("input", json!({
//!             "messages": [{"role": "user", "content": "Analyze this data"}]
//!         }))
//!     ]).await?;
//!     
//!     while let Some(chunk) = stream.next().await {
//!         match chunk {
//!             Ok(data) => {
//!                 if let Some(node) = data.get("node") {
//!                     println!("Executing node: {}", node);
//!                 }
//!             }
//!             Err(e) => eprintln!("Error: {}", e),
//!         }
//!     }
//!     
//!     Ok(())
//! }
//! ```
//!
//! ## Configuration
//!
//! ### Using Environment Variables
//!
//! Set these environment variables for configuration:
//!
//! ```bash
//! export RUNAGENT_API_KEY="your-api-key"
//! export RUNAGENT_BASE_URL="https://api.runagent.ai"
//! export RUNAGENT_CACHE_DIR="~/.runagent"
//! export RUNAGENT_LOGGING_LEVEL="info"
//! ```
//!
//! ### Using Configuration Builder
//!
//! ```rust,no_run
//! use runagent::RunAgentConfig;
//!
//! let config = RunAgentConfig::new()
//!     .with_api_key("your-api-key")
//!     .with_base_url("https://api.runagent.ai")
//!     .with_logging()
//!     .build();
//! ```
//!
//! ## Database Management
//!
//! ```rust,no_run
//! use runagent::db::{DatabaseService, models::Agent};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Initialize database service
//!     let db_service = DatabaseService::new(None).await?;
//!     
//!     // Create a new agent record
//!     let agent = Agent::new(
//!         "my-agent".to_string(),
//!         "/path/to/agent".to_string(),
//!         "localhost".to_string(),
//!         8450
//!     ).with_framework("langchain".to_string());
//!     
//!     // Add agent to database
//!     let result = db_service.add_agent(agent).await?;
//!     println!("Agent added: {:?}", result);
//!     
//!     // List all agents
//!     let agents = db_service.list_agents().await?;
//!     for agent in agents {
//!         println!("Agent: {} ({}:{})", agent.agent_id, agent.host, agent.port);
//!     }
//!     
//!     Ok(())
//! }
//! ```
//!
//! ## Error Handling
//!
//! The SDK provides comprehensive error handling with specific error types:
//!
//
//! ```rust,no_run
//! use runagent::{RunAgentError, RunAgentResult};
//!
//! fn handle_errors() -> RunAgentResult<()> {
//!     // Your operation here
//!     match some_operation() {
//!         Ok(result) => {
//!             println!("Success: {}", result);
//!             Ok(())
//!         },
//!         Err(RunAgentError::Authentication { message }) => {
//!             eprintln!("Auth error: {}", message);
//!             Err(RunAgentError::authentication("Invalid credentials"))
//!         }
//!         Err(RunAgentError::Connection { message }) => {
//!             eprintln!("Connection error: {}", message);
//!             // Retry logic for retryable errors
//!             if message.contains("retryable") {
//!                 retry_operation()
//!             } else {
//!                 Err(RunAgentError::connection("Connection failed"))
//!             }
//!         }
//!         Err(e) => Err(e),
//!     }
//! }
//! 
//! fn some_operation() -> RunAgentResult<String> { 
//!     Ok("test".to_string()) 
//! }
//! 
//! fn retry_operation() -> RunAgentResult<()> { 
//!     Ok(()) 
//! }
//! ```
//!
//! ## Features
//!
//! The SDK supports optional features that can be enabled/disabled:
//!
//! ```toml
//! [dependencies]
//! runagent = { version = "0.1.0", features = ["db", "server"] }
//! ```
//!
//! Available features:
//! - `db` (default): Database functionality for agent metadata storage
//! - `server` (default): Local server capabilities for testing
//!
//! ## Architecture Overview
//!
//! The RunAgent SDK is built around several core components:
//!
//! - **Client Components**: High-level clients for interacting with deployed agents
//! - **Local Server**: FastAPI-like local server for testing agents
//! - **Database Management**: SQLite-based storage for agent metadata
//! - **Multi-Framework Support**: Support for LangChain, LangGraph, LlamaIndex, and more
//! - **Streaming Support**: WebSocket-based streaming for real-time agent interactions
//!
//! Each component is designed to work independently or together, allowing you to use
//! only the parts you need for your specific use case.

pub mod client;
pub mod constants;
pub mod types;
pub mod utils;

#[cfg(feature = "server")]
pub mod server;

#[cfg(feature = "db")]
pub mod db;

// Re-export commonly used types and functions
pub use client::{RunAgentClient, RestClient, SocketClient};
pub use types::{RunAgentError, RunAgentResult};

#[cfg(feature = "server")]
pub use server::LocalServer;

#[cfg(feature = "db")]
pub use db::{DatabaseService, DatabaseManager};

// Version information
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Initialize logging for the RunAgent SDK
///
/// This sets up structured logging with configurable levels via the
/// `RUNAGENT_LOGGING_LEVEL` environment variable.
///
/// # Example
///
/// ```rust,no_run
/// runagent::init_logging();
/// tracing::info!("RunAgent SDK initialized");
/// ```
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("runagent=info".parse().unwrap())
        )
        .init();
}

/// Configuration builder for the RunAgent SDK
///
/// Provides a fluent interface for configuring the SDK with various options
/// including API keys, base URLs, database paths, and logging.
///
/// # Example
///
/// ```rust,no_run
/// use runagent::RunAgentConfig;
///
/// let config = RunAgentConfig::new()
///     .with_api_key("your-api-key")
///     .with_base_url("https://api.runagent.ai")
///     .with_logging()
///     .build();
/// ```
#[derive(Default)]
pub struct RunAgentConfig {
    /// Optional API key for authentication
    pub api_key: Option<String>,
    /// Base URL for API endpoints
    pub base_url: Option<String>,
    /// Path to local database file
    pub local_db_path: Option<std::path::PathBuf>,
    /// Whether to enable logging
    pub enable_logging: bool,
}

impl RunAgentConfig {
    /// Create a new configuration builder
    ///
    /// # Example
    ///
    /// ```rust
    /// use runagent::RunAgentConfig;
    /// let config = RunAgentConfig::new();
    /// ```
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the API key for authentication
    ///
    /// # Arguments
    ///
    /// * `api_key` - The API key string
    ///
    /// # Example
    ///
    /// ```rust
    /// use runagent::RunAgentConfig;
    /// let config = RunAgentConfig::new().with_api_key("your-api-key");
    /// ```
    pub fn with_api_key<S: Into<String>>(mut self, api_key: S) -> Self {
        self.api_key = Some(api_key.into());
        self
    }

    /// Set the base URL for API endpoints
    ///
    /// # Arguments
    ///
    /// * `base_url` - The base URL string
    ///
    /// # Example
    ///
    /// ```rust
    /// use runagent::RunAgentConfig;
    /// let config = RunAgentConfig::new().with_base_url("https://api.runagent.ai");
    /// ```
    pub fn with_base_url<S: Into<String>>(mut self, base_url: S) -> Self {
        self.base_url = Some(base_url.into());
        self
    }

    /// Set the local database path
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the database file
    ///
    /// # Example
    ///
    /// ```rust
    /// use runagent::RunAgentConfig;
    /// use std::path::PathBuf;
    /// 
    /// let config = RunAgentConfig::new()
    ///     .with_local_db_path(PathBuf::from("./my_agents.db"));
    /// ```
    pub fn with_local_db_path<P: Into<std::path::PathBuf>>(mut self, path: P) -> Self {
        self.local_db_path = Some(path.into());
        self
    }

    /// Enable logging initialization
    ///
    /// When enabled, the `build()` method will automatically initialize
    /// the logging system.
    ///
    /// # Example
    ///
    /// ```rust
    /// use runagent::RunAgentConfig;
    /// let config = RunAgentConfig::new().with_logging();
    /// ```
    pub fn with_logging(mut self) -> Self {
        self.enable_logging = true;
        self
    }

    /// Build the configuration and optionally initialize logging
    ///
    /// If logging was enabled via `with_logging()`, this will initialize
    /// the tracing subscriber.
    ///
    /// # Example
    ///
    /// ```rust
    /// use runagent::RunAgentConfig;
    /// let config = RunAgentConfig::new()
    ///     .with_logging()
    ///     .build();
    /// ```
    pub fn build(self) -> Self {
        if self.enable_logging {
            init_logging();
        }
        self
    }
}

/// Prelude module for convenient imports
///
/// This module re-exports the most commonly used types and functions
/// from the RunAgent SDK for easy importing.
///
/// # Example
///
/// ```rust,no_run
/// use runagent::prelude::*;
/// 
/// // Now you have access to RunAgentClient, RunAgentError, etc.
/// ```
pub mod prelude {
    pub use crate::client::{RunAgentClient, RestClient, SocketClient};
    pub use crate::types::{RunAgentError, RunAgentResult};
    pub use crate::RunAgentConfig;
    
    #[cfg(feature = "server")]
    pub use crate::server::LocalServer;
    
    #[cfg(feature = "db")]
    pub use crate::db::{DatabaseService, DatabaseManager};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_version() {
        assert!(!VERSION.is_empty());
    }

    #[test]
    fn test_config_builder() {
        let config = RunAgentConfig::new()
            .with_api_key("test-key")
            .with_base_url("http://localhost:8000")
            .build();

        assert_eq!(config.api_key.as_deref(), Some("test-key"));
        assert_eq!(config.base_url.as_deref(), Some("http://localhost:8000"));
    }

    #[test]
    fn test_config_default() {
        let config = RunAgentConfig::default();
        assert!(config.api_key.is_none());
        assert!(config.base_url.is_none());
        assert!(!config.enable_logging);
    }
}