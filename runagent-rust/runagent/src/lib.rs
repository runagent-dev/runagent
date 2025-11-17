//! # RunAgent Rust SDK
//!
//! A comprehensive Rust SDK for deploying and managing AI agents with support for multiple
//! frameworks including LangChain, LangGraph, LlamaIndex, and more.
//!
//! ## Features
//!
//! - **Client SDK**: REST and WebSocket clients for interacting with deployed agents
//! - **Real-time Streaming**: WebSocket-based streaming for real-time agent interactions
//! - **Type Safety**: Full Rust type safety with comprehensive error handling
//! - **Async/Await**: Built on Tokio for high-performance async operations
//!
//! ## Quick Start
//!
//! ### Basic Agent Interaction
//!
//! ```rust,no_run
//! use runagent::{RunAgentClient, RunAgentClientConfig};
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Initialize logging
//!     runagent::init_logging();
//!
//!     // Create a client for a local agent
//!     let client = RunAgentClient::new(RunAgentClientConfig {
//!         agent_id: "my-agent-id".to_string(),
//!         entrypoint_tag: "generic".to_string(),
//!         local: Some(true),
//!         ..RunAgentClientConfig::default()
//!     }).await?;
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
//! use runagent::{RunAgentClient, RunAgentClientConfig};
//! use futures::StreamExt;
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = RunAgentClient::new(RunAgentClientConfig {
//!         agent_id: "my-agent-id".to_string(),
//!         entrypoint_tag: "generic_stream".to_string(),
//!         local: Some(true),
//!         ..RunAgentClientConfig::default()
//!     }).await?;
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
//! ### Connecting to Local Agents
//!
//! ```rust,no_run
//! use runagent::{RunAgentClient, RunAgentClientConfig};
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Connect to a local agent running on localhost:8450
//!     let client = RunAgentClient::new(RunAgentClientConfig {
//!         agent_id: "my-agent-id".to_string(),
//!         entrypoint_tag: "generic".to_string(),
//!         local: Some(true),
//!         host: Some("127.0.0.1".to_string()),
//!         port: Some(8450),
//!         ..RunAgentClientConfig::default()
//!     }).await?;
//!     
//!     let response = client.run(&[
//!         ("message", json!("Hello, world!"))
//!     ]).await?;
//!     
//!     println!("Response: {}", response);
//!     Ok(())
//! }
//! ```
//!
//! ## Framework-Specific Examples
//!
//! ### LangChain Integration
//!
//! ```rust,no_run
//! use runagent::{RunAgentClient, RunAgentClientConfig};
//! use serde_json::json;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = RunAgentClient::new(RunAgentClientConfig {
//!         agent_id: "langchain-agent".to_string(),
//!         entrypoint_tag: "invoke".to_string(),
//!         local: Some(true),
//!         ..RunAgentClientConfig::default()
//!     }).await?;
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
//! use runagent::{RunAgentClient, RunAgentClientConfig};
//! use serde_json::json;
//! use futures::StreamExt;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let client = RunAgentClient::new(RunAgentClientConfig {
//!         agent_id: "langgraph-agent".to_string(),
//!         entrypoint_tag: "stream".to_string(),
//!         local: Some(true),
//!         ..RunAgentClientConfig::default()
//!     }).await?;
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
//! ## Architecture Overview
//!
//! The RunAgent SDK focuses on client-side functionality for interacting with agents:
//!
//! - **Client Components**: High-level REST and WebSocket clients for interacting with deployed agents
//! - **Configuration Management**: Environment-based and programmatic configuration
//! - **Streaming Support**: WebSocket-based streaming for real-time agent interactions
//! - **Type Safety**: Comprehensive error handling and type definitions

pub mod client;
pub mod constants;
pub mod types;
pub mod utils;

#[cfg(feature = "db")]
pub mod db;

/// Blocking (synchronous) wrapper for RunAgentClient
///
/// This module provides a synchronous interface that wraps the async client.
/// It's useful for simple scripts or when you can't use async/await.
///
/// # Example
///
/// ```rust,no_run
/// use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
/// use serde_json::json;
///
/// fn main() -> runagent::RunAgentResult<()> {
///     let client = RunAgentClient::new(
///         RunAgentClientConfig::new("agent-id", "entrypoint")
///             .with_api_key("key")
///     )?;
///
///     let result = client.run(&[("message", json!("Hello"))])?;
///     Ok(())
/// }
/// ```
pub mod blocking;

// Re-export commonly used types and functions
pub use client::{RunAgentClient, RunAgentClientConfig, RestClient, SocketClient};
pub use types::{RunAgentError, RunAgentResult};

// Re-export blocking client for convenience
pub use blocking::{RunAgentClient as BlockingRunAgentClient, BlockingStream};

#[cfg(feature = "db")]
pub use db::DatabaseService;

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
/// including API keys, base URLs, and logging.
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
    pub use crate::client::{RunAgentClient, RunAgentClientConfig, RestClient, SocketClient};
    pub use crate::types::{RunAgentError, RunAgentResult};
    
    #[cfg(feature = "db")]
    pub use crate::db::DatabaseService;
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