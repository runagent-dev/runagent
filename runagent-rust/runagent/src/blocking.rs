//! Blocking (synchronous) wrapper for RunAgentClient
//!
//! This module provides a synchronous interface that wraps the async client.
//! It uses a Tokio runtime internally to block on async operations.
//!
//! # Example
//!
//! ```rust,no_run
//! use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
//! use serde_json::json;
//!
//! fn main() -> runagent::RunAgentResult<()> {
//!     let client = RunAgentClient::new(
//!         RunAgentClientConfig::new("agent-id", "entrypoint")
//!             .with_api_key(Some("key".to_string()))
//!     )?;
//!
//!     let result = client.run(&[("message", json!("Hello"))])?;
//!     println!("Result: {}", result);
//!     Ok(())
//! }
//! ```

use crate::client::RunAgentClient as AsyncRunAgentClient;
use crate::types::{RunAgentError, RunAgentResult};
use serde_json::Value;
use std::collections::HashMap;
use tokio::runtime::Runtime;

// Re-export for convenience
pub use crate::client::RunAgentClientConfig;

/// Blocking (synchronous) wrapper for RunAgentClient
///
/// This client wraps the async client and blocks on async operations.
/// It's useful for simple scripts or when you can't use async/await.
///
/// Note: For better performance and resource usage, prefer the async client.
pub struct RunAgentClient {
    inner: AsyncRunAgentClient,
    runtime: Runtime,
}

impl RunAgentClient {
    /// Create a new blocking RunAgent client
    ///
    /// This will create a Tokio runtime internally and block until the client is initialized.
    pub fn new(config: RunAgentClientConfig) -> RunAgentResult<Self> {
        let runtime = Runtime::new()
            .map_err(|e| RunAgentError::connection(format!("Failed to create runtime: {}", e)))?;

        let inner = runtime.block_on(AsyncRunAgentClient::new(config))?;

        Ok(Self { inner, runtime })
    }

    /// Execute a non-streaming entrypoint
    ///
    /// This blocks until the agent execution completes.
    pub fn run(&self, input_kwargs: &[(&str, Value)]) -> RunAgentResult<Value> {
        self.runtime.block_on(self.inner.run(input_kwargs))
    }

    /// Execute a non-streaming entrypoint with both args and kwargs
    pub fn run_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Value> {
        self.runtime
            .block_on(self.inner.run_with_args(input_args, input_kwargs))
    }

    /// Execute a streaming entrypoint
    ///
    /// Returns a vector of all chunks collected from the stream.
    /// Note: This collects the entire stream, so it's not truly streaming.
    /// For real streaming, use the async client.
    pub fn run_stream(
        &self,
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Vec<RunAgentResult<Value>>> {
        let stream = self.runtime.block_on(self.inner.run_stream(input_kwargs))?;
        Ok(self.runtime.block_on(async {
            use futures::StreamExt;
            let mut results = Vec::new();
            let mut stream = stream;
            while let Some(item) = stream.next().await {
                results.push(item);
            }
            results
        }))
    }

    /// Execute a streaming entrypoint with both args and kwargs
    pub fn run_stream_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Vec<RunAgentResult<Value>>> {
        let stream = self
            .runtime
            .block_on(self.inner.run_stream_with_args(input_args, input_kwargs))?;
        Ok(self.runtime.block_on(async {
            use futures::StreamExt;
            let mut results = Vec::new();
            let mut stream = stream;
            while let Some(item) = stream.next().await {
                results.push(item);
            }
            results
        }))
    }

    /// Get agent architecture
    pub fn get_agent_architecture(&self) -> RunAgentResult<Value> {
        self.runtime.block_on(self.inner.get_agent_architecture())
    }

    /// Health check
    pub fn health_check(&self) -> RunAgentResult<bool> {
        self.runtime.block_on(self.inner.health_check())
    }

    /// Get agent ID
    pub fn agent_id(&self) -> &str {
        self.inner.agent_id()
    }

    /// Get entrypoint tag
    pub fn entrypoint_tag(&self) -> &str {
        self.inner.entrypoint_tag()
    }

    /// Get extra parameters
    pub fn extra_params(&self) -> Option<&HashMap<String, Value>> {
        self.inner.extra_params()
    }

    /// Check if this is a local client
    pub fn is_local(&self) -> bool {
        self.inner.is_local()
    }
}

