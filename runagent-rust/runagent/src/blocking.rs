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
//!             .with_api_key("key")
//!     )?;
//!
//!     let result = client.run(&[("message", json!("Hello"))])?;
//!     println!("Result: {}", result);
//!     Ok(())
//! }
//! ```

use crate::client::RunAgentClient as AsyncRunAgentClient;
use crate::types::{RunAgentError, RunAgentResult};
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::pin::Pin;
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
    /// Returns a blocking iterator that yields chunks as they arrive.
    /// This provides true streaming - chunks are processed incrementally,
    /// not collected all at once.
    ///
    /// # Example
    ///
    /// ```rust,no_run
    /// use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
    /// use serde_json::json;
    ///
    /// fn main() -> runagent::RunAgentResult<()> {
    ///     let client = RunAgentClient::new(
    ///         RunAgentClientConfig::new("agent-id", "entrypoint_stream")
    ///             .with_api_key("key")
    ///     )?;
    ///
    ///     let mut stream = client.run_stream(&[("message", json!("Hello"))])?;
    ///     while let Some(chunk) = stream.next() {
    ///         println!(">> {}", chunk?);
    ///     }
    ///     Ok(())
    /// }
    /// ```
    pub fn run_stream(
        &self,
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<BlockingStream> {
        let stream = self.runtime.block_on(self.inner.run_stream(input_kwargs))?;
        Ok(BlockingStream::new(stream))
    }

    /// Execute a streaming entrypoint with both args and kwargs
    ///
    /// Returns a blocking iterator that yields chunks as they arrive.
    /// This provides true streaming - chunks are processed incrementally,
    /// not collected all at once.
    pub fn run_stream_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<BlockingStream> {
        let stream = self
            .runtime
            .block_on(self.inner.run_stream_with_args(input_args, input_kwargs))?;
        Ok(BlockingStream::new(stream))
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

/// Blocking iterator over a streaming response
///
/// This iterator yields chunks as they arrive from the agent,
/// blocking on each `next()` call until a chunk is available.
///
/// # Example
///
/// ```rust,no_run
/// use runagent::blocking::{RunAgentClient, RunAgentClientConfig, BlockingStream};
/// use serde_json::json;
///
/// fn main() -> runagent::RunAgentResult<()> {
///     let client = RunAgentClient::new(RunAgentClientConfig {
///         agent_id: "agent-id".to_string(),
///         entrypoint_tag: "entrypoint_stream".to_string(),
///         ..RunAgentClientConfig::default()
///     })?;
///     
///     let mut stream = client.run_stream(&[("message", json!("Hello"))])?;
///     while let Some(chunk) = stream.next() {
///         match chunk {
///             Ok(value) => println!("Chunk: {}", value),
///             Err(e) => eprintln!("Error: {}", e),
///         }
///     }
///     Ok(())
/// }
/// ```
pub struct BlockingStream {
    receiver: std::sync::mpsc::Receiver<RunAgentResult<Value>>,
    _handle: std::thread::JoinHandle<()>, // Keep the background task alive
}

impl BlockingStream {
    pub(crate) fn new(
        mut stream: Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>,
    ) -> Self {
        use futures::StreamExt;
        use std::sync::mpsc;
        use std::thread;
        
        let (tx, rx) = mpsc::channel();
        
        // Spawn a background task that continuously polls the stream
        let handle = thread::spawn(move || {
            // Create a new runtime for the background thread
            let rt = Runtime::new().expect("Failed to create runtime");
            rt.block_on(async move {
                while let Some(item) = stream.next().await {
                    if tx.send(item).is_err() {
                        // Receiver dropped, stop polling
                        break;
                    }
                }
            });
        });
        
        Self {
            receiver: rx,
            _handle: handle,
        }
    }
}

impl Iterator for BlockingStream {
    type Item = RunAgentResult<Value>;

    fn next(&mut self) -> Option<Self::Item> {
        self.receiver.recv().ok()
    }
}

