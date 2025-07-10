//! # RunAgent Rust SDK
//!
//! A comprehensive Rust SDK for deploying and managing AI agents.
//!
//! ## Features
//!
//! - **Client Components**: Interact with local and remote RunAgent deployments
//! - **Local Server**: FastAPI-like local server for testing agents
//! - **Database Management**: SQLite-based storage for agent metadata
//! - **Multi-Framework Support**: Support for LangChain, LangGraph, LlamaIndex, and more
//! - **Streaming Support**: WebSocket-based streaming for real-time agent interactions
//!
//! ## Quick Start
//!
//! ```rust,no_run
//! use runagent::client::RunAgentClient;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     // Create a client for a local agent
//!     let client = RunAgentClient::new("my-agent-id", "generic", true).await?;
//!     
//!     // Run the agent
//!     let response = client.run(&[
//!         ("message", serde_json::json!("Hello, world!"))
//!     ]).await?;
//!     
//!     println!("Response: {}", response);
//!     Ok(())
//! }
//! ```

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
pub fn init_logging() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive("runagent=info".parse().unwrap())
        )
        .init();
}

/// Configuration builder for the RunAgent SDK
#[derive(Default)]
pub struct RunAgentConfig {
    pub api_key: Option<String>,
    pub base_url: Option<String>,
    pub local_db_path: Option<std::path::PathBuf>,
    pub enable_logging: bool,
}

impl RunAgentConfig {
    /// Create a new configuration builder
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the API key
    pub fn with_api_key<S: Into<String>>(mut self, api_key: S) -> Self {
        self.api_key = Some(api_key.into());
        self
    }

    /// Set the base URL
    pub fn with_base_url<S: Into<String>>(mut self, base_url: S) -> Self {
        self.base_url = Some(base_url.into());
        self
    }

    /// Set the local database path
    pub fn with_local_db_path<P: Into<std::path::PathBuf>>(mut self, path: P) -> Self {
        self.local_db_path = Some(path.into());
        self
    }

    /// Enable logging
    pub fn with_logging(mut self) -> Self {
        self.enable_logging = true;
        self
    }

    /// Build the configuration and optionally initialize logging
    pub fn build(self) -> Self {
        if self.enable_logging {
            init_logging();
        }
        self
    }
}

/// Prelude module for convenient imports
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
}