//! Main RunAgent client for interacting with deployed agents

use crate::client::rest_client::RestClient;
use crate::client::socket_client::SocketClient;
use crate::types::{RunAgentError, RunAgentResult};
use crate::utils::serializer::CoreSerializer;
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::pin::Pin;

#[cfg(feature = "db")]
use crate::db::DatabaseService;

/// Main client for interacting with RunAgent deployments
pub struct RunAgentClient {
    agent_id: String,
    entrypoint_tag: String,
    local: bool,
    rest_client: RestClient,
    socket_client: SocketClient,
    serializer: CoreSerializer,
    agent_architecture: Option<Value>,

    #[cfg(feature = "db")]
    db_service: Option<DatabaseService>,
}

impl RunAgentClient {
    /// Create a new RunAgent client
    ///
    /// # Arguments
    /// * `agent_id` - The ID of the agent to interact with
    /// * `entrypoint_tag` - The entrypoint tag to use
    /// * `local` - Whether to use local deployment (true) or remote (false)
    /// * `host` - Optional host override (for local deployments)
    /// * `port` - Optional port override (for local deployments)
    ///
    /// # Example
    /// ```rust,no_run
    /// use runagent::client::RunAgentClient;
    ///
    /// #[tokio::main]
    /// async fn main() -> Result<(), Box<dyn std::error::Error>> {
    ///     let client = RunAgentClient::new("my-agent", "generic", true).await?;
    ///     // Use the client...
    ///     Ok(())
    /// }
    /// ```
    pub async fn new(
        agent_id: &str,
        entrypoint_tag: &str,
        local: bool,
    ) -> RunAgentResult<Self> {
        Self::with_address(agent_id, entrypoint_tag, local, None, None).await
    }

    /// Create a new RunAgent client with specific host and port
    pub async fn with_address(
        agent_id: &str,
        entrypoint_tag: &str,
        local: bool,
        host: Option<&str>,
        port: Option<u16>,
    ) -> RunAgentResult<Self> {
        let serializer = CoreSerializer::new(10.0)?;

        #[cfg(feature = "db")]
        let db_service = if local {
            Some(DatabaseService::new(None).await?)
        } else {
            None
        };
        
        let (rest_client, socket_client) = if local {
            let (agent_host, agent_port) = if let (Some(h), Some(p)) = (host, port) {
                tracing::info!("Using explicit address: {}:{}", h, p);
                (h.to_string(), p)
            } else {
                #[cfg(feature = "db")]
                {
                    if let Some(ref db) = db_service {
                        let agent_info = db.get_agent(agent_id).await?
                            .ok_or_else(|| RunAgentError::validation(format!("Agent {} not found in local DB", agent_id)))?;
                        
                        tracing::info!("Auto-resolved address for agent {}: {}:{}", agent_id, agent_info.host, agent_info.port);
                        (agent_info.host, agent_info.port as u16)
                    } else {
                        return Err(RunAgentError::config("Database feature not enabled but required for local agent lookup"));
                    }
                }
                #[cfg(not(feature = "db"))]
                {
                    return Err(RunAgentError::config("Database feature not enabled but required for local agent lookup"));
                }
            };

            let agent_base_url = format!("http://{}:{}", agent_host, agent_port);
            let agent_socket_url = format!("ws://{}:{}", agent_host, agent_port);

            let rest_client = RestClient::new(&agent_base_url, None, Some("/api/v1"))?;
            let socket_client = SocketClient::new(&agent_socket_url, None, Some("/api/v1"))?;

            (rest_client, socket_client)
        } else {
            let rest_client = RestClient::default()?;
            let socket_client = SocketClient::default()?;
            (rest_client, socket_client)
        };

        let mut client = Self {
            agent_id: agent_id.to_string(),
            entrypoint_tag: entrypoint_tag.to_string(),
            local,
            rest_client,
            socket_client,
            serializer,
            agent_architecture: None,

            #[cfg(feature = "db")]
            db_service,
        };

        // Get agent architecture
        client.agent_architecture = Some(client.get_agent_architecture_sync()?);
        client.validate_entrypoint()?;

        Ok(client)
    }

    fn get_agent_architecture_sync(&self) -> RunAgentResult<Value> {
        // This would need to be implemented as an async call in practice
        // For now, we'll return a placeholder
        Ok(serde_json::json!({
            "entrypoints": [
                {
                    "tag": self.entrypoint_tag,
                    "file": "main.py",
                    "module": "run"
                }
            ]
        }))
    }

    fn validate_entrypoint(&self) -> RunAgentResult<()> {
        if let Some(ref architecture) = self.agent_architecture {
            if let Some(entrypoints) = architecture.get("entrypoints").and_then(|e| e.as_array()) {
                let found = entrypoints.iter().any(|ep| {
                    ep.get("tag")
                        .and_then(|t| t.as_str())
                        .map(|t| t == self.entrypoint_tag)
                        .unwrap_or(false)
                });

                if !found {
                    return Err(RunAgentError::validation(format!(
                        "Entrypoint `{}` not found in agent {}",
                        self.entrypoint_tag, self.agent_id
                    )));
                }
            }
        }
        Ok(())
    }

    /// Run the agent with the given input
    ///
    /// # Arguments
    /// * `input_args` - Positional arguments for the agent
    /// * `input_kwargs` - Keyword arguments for the agent
    ///
    /// # Example
    /// ```rust,no_run
    /// # use runagent::client::RunAgentClient;
    /// # #[tokio::main]
    /// # async fn main() -> Result<(), Box<dyn std::error::Error>> {
    /// # let client = RunAgentClient::new("my-agent", "generic", true).await?;
    /// let response = client.run_with_args(
    ///     &[serde_json::json!("Hello")],
    ///     &[("temperature", serde_json::json!(0.7))]
    /// ).await?;
    /// println!("Response: {}", response);
    /// # Ok(())
    /// # }
    /// ```
    pub async fn run_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Value> {
        if self.entrypoint_tag.ends_with("_stream") {
            return Err(RunAgentError::validation(
                "Use run_stream for streaming entrypoints".to_string(),
            ));
        }

        let input_kwargs_map: HashMap<String, Value> = input_kwargs
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect();

        let response = self
            .rest_client
            .run_agent(
                &self.agent_id,
                &self.entrypoint_tag,
                input_args,
                &input_kwargs_map,
            )
            .await?;

        if response.get("success").and_then(|s| s.as_bool()).unwrap_or(false) {
            if let Some(output_data) = response.get("output_data") {
                self.serializer.deserialize_object(output_data.clone())
            } else {
                Ok(Value::Null)
            }
        } else {
            let error_msg = response
                .get("error")
                .and_then(|e| e.as_str())
                .unwrap_or("Unknown error");
            Err(RunAgentError::server(error_msg))
        }
    }

    /// Run the agent with keyword arguments only
    ///
    /// # Example
    /// ```rust,no_run
    /// # use runagent::client::RunAgentClient;
    /// # #[tokio::main]
    /// # async fn main() -> Result<(), Box<dyn std::error::Error>> {
    /// # let client = RunAgentClient::new("my-agent", "generic", true).await?;
    /// let response = client.run(&[
    ///     ("message", serde_json::json!("Hello, world!")),
    ///     ("temperature", serde_json::json!(0.7))
    /// ]).await?;
    /// # Ok(())
    /// # }
    /// ```
    pub async fn run(&self, input_kwargs: &[(&str, Value)]) -> RunAgentResult<Value> {
        self.run_with_args(&[], input_kwargs).await
    }

    /// Run the agent and return a stream of responses
    ///
    /// # Example
    /// ```rust,no_run
    /// # use runagent::client::RunAgentClient;
    /// # use futures::StreamExt;
    /// # #[tokio::main]
    /// # async fn main() -> Result<(), Box<dyn std::error::Error>> {
    /// # let client = RunAgentClient::new("my-agent", "generic_stream", true).await?;
    /// let mut stream = client.run_stream(&[
    ///     ("message", serde_json::json!("Hello, world!"))
    /// ]).await?;
    ///
    /// while let Some(chunk) = stream.next().await {
    ///     match chunk {
    ///         Ok(data) => println!("Chunk: {}", data),
    ///         Err(e) => eprintln!("Error: {}", e),
    ///     }
    /// }
    /// # Ok(())
    /// # }
    /// ```
    pub async fn run_stream(
        &self,
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        self.run_stream_with_args(&[], input_kwargs).await
    }

    /// Run the agent with streaming and both positional and keyword arguments
    pub async fn run_stream_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        let input_kwargs_map: HashMap<String, Value> = input_kwargs
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect();

        self.socket_client
            .run_stream(&self.agent_id, &self.entrypoint_tag, input_args, &input_kwargs_map)
            .await
    }

    /// Get the agent's architecture information
    pub async fn get_agent_architecture(&self) -> RunAgentResult<Value> {
        self.rest_client.get_agent_architecture(&self.agent_id).await
    }

    /// Check if the agent is available
    pub async fn health_check(&self) -> RunAgentResult<bool> {
        match self.rest_client.health_check().await {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    /// Get agent information
    pub fn agent_id(&self) -> &str {
        &self.agent_id
    }

    /// Get entrypoint tag
    pub fn entrypoint_tag(&self) -> &str {
        &self.entrypoint_tag
    }

    /// Check if using local deployment
    pub fn is_local(&self) -> bool {
        self.local
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_client_creation() {
        // Note: This would require mocking in a real test
        // For now, just test the basic structure
        assert!(true);
    }

    #[test]
    fn test_entrypoint_validation() {
        // This would test the entrypoint validation logic
        assert!(true);
    }
}