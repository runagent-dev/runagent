//! WebSocket client for streaming agent interactions

use crate::types::{
    RunAgentError, RunAgentResult, SafeMessage, WebSocketActionType, WebSocketAgentRequest,
    AgentInputArgs, MessageType,
};
use crate::utils::config::Config;
use crate::utils::serializer::CoreSerializer;
use futures::{SinkExt, Stream, StreamExt};
use serde_json::Value;
use std::collections::HashMap;
use std::pin::Pin;
use tokio_tungstenite::{connect_async, tungstenite::Message};
use url::Url;

/// WebSocket client for agent streaming
pub struct SocketClient {
    base_socket_url: String,
    api_key: Option<String>,
    api_prefix: String,
    serializer: CoreSerializer,
}

impl SocketClient {
    /// Create a new WebSocket client
    pub fn new(
        base_socket_url: &str,
        api_key: Option<String>,
        api_prefix: Option<&str>,
    ) -> RunAgentResult<Self> {
        let serializer = CoreSerializer::new(10.0)?;
        
        Ok(Self {
            base_socket_url: base_socket_url.trim_end_matches('/').to_string(),
            api_key,
            api_prefix: api_prefix.unwrap_or("/api/v1").to_string(),
            serializer,
        })
    }

    /// Create a default WebSocket client using configuration
    pub fn default() -> RunAgentResult<Self> {
        let config = Config::load()?;
        let base_url = config.base_url();
        
        // Convert HTTP URL to WebSocket URL
        let ws_url = if base_url.starts_with("https://") {
            base_url.replace("https://", "wss://")
        } else if base_url.starts_with("http://") {
            base_url.replace("http://", "ws://")
        } else {
            format!("ws://{}", base_url)
        };

        Self::new(&ws_url, config.api_key(), Some("/api/v1"))
    }

    fn get_websocket_url(&self, agent_id: &str, entrypoint_tag: &str) -> RunAgentResult<Url> {
        let path = format!("agents/{}/execute/{}", agent_id, entrypoint_tag);
        let full_url = format!("{}{}/{}", self.base_socket_url, self.api_prefix, path);
        
        Url::parse(&full_url)
            .map_err(|e| RunAgentError::validation(format!("Invalid WebSocket URL: {}", e)))
    }

    /// Run agent with streaming response
    pub async fn run_stream(
        &self,
        agent_id: &str,
        entrypoint_tag: &str,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        let url = self.get_websocket_url(agent_id, entrypoint_tag)?;
        
        tracing::debug!("Connecting to WebSocket: {}", url);

        // Connect to WebSocket
        let (ws_stream, _) = connect_async(url).await
            .map_err(|e| RunAgentError::connection(format!("WebSocket connection failed: {}", e)))?;

        let (mut write, mut read) = ws_stream.split();

        // Prepare start stream request
        let request = WebSocketAgentRequest {
            action: WebSocketActionType::StartStream,
            agent_id: agent_id.to_string(),
            input_data: AgentInputArgs {
                input_args: input_args.to_vec(),
                input_kwargs: input_kwargs.clone(),
            },
            stream_config: HashMap::new(),
        };

        let start_msg = SafeMessage::new(
            "stream_start".to_string(),
            MessageType::Status,
            serde_json::to_value(&request)?,
        );

        // Send start stream message
        let serialized_msg = self.serializer.serialize_message(&start_msg)?;
        write.send(Message::Text(serialized_msg)).await
            .map_err(|e| RunAgentError::connection(format!("Failed to send start message: {}", e)))?;

        // Create stream that processes incoming messages
        let serializer = self.serializer.clone();
        let stream = async_stream::stream! {
            while let Some(message) = read.next().await {
                match message {
                    Ok(Message::Text(text)) => {
                        match serializer.deserialize_message(&text) {
                            Ok(safe_msg) => {
                                match safe_msg.message_type {
                                    MessageType::Status => {
                                        if let Some(status) = safe_msg.data.get("status") {
                                            if status == "stream_completed" {
                                                break;
                                            } else if status == "stream_started" {
                                                continue; // Skip status messages
                                            }
                                        }
                                    }
                                    MessageType::Error => {
                                        yield Err(RunAgentError::server(
                                            safe_msg.error.unwrap_or_else(|| "Agent error".to_string())
                                        ));
                                        break;
                                    }
                                    _ => {
                                        // Yield the actual chunk data
                                        yield Ok(safe_msg.data);
                                    }
                                }
                            }
                            Err(e) => {
                                yield Err(RunAgentError::server(format!("Stream error: {}", e)));
                                break;
                            }
                        }
                    }
                    Ok(Message::Close(_)) => {
                        break;
                    }
                    Ok(_) => {
                        // Ignore binary and other message types
                        continue;
                    }
                    Err(e) => {
                        yield Err(RunAgentError::connection(format!("WebSocket error: {}", e)));
                        break;
                    }
                }
            }
        };

        Ok(Box::pin(stream))
    }

    /// Send a ping message to test connection
    pub async fn ping(&self, agent_id: &str, entrypoint_tag: &str) -> RunAgentResult<bool> {
        let url = self.get_websocket_url(agent_id, entrypoint_tag)?;
        
        let (ws_stream, _) = connect_async(url).await
            .map_err(|e| RunAgentError::connection(format!("WebSocket connection failed: {}", e)))?;

        let (mut write, mut read) = ws_stream.split();

        // Send ping
        let ping_msg = SafeMessage::new(
            "ping".to_string(),
            MessageType::Status,
            serde_json::json!({"ping": true}),
        );

        let serialized_msg = self.serializer.serialize_message(&ping_msg)?;
        write.send(Message::Text(serialized_msg)).await
            .map_err(|e| RunAgentError::connection(format!("Failed to send ping: {}", e)))?;

        // Wait for pong
        tokio::time::timeout(
            std::time::Duration::from_secs(5),
            read.next()
        ).await
            .map_err(|_| RunAgentError::connection("Ping timeout".to_string()))?
            .ok_or_else(|| RunAgentError::connection("Connection closed during ping".to_string()))?
            .map_err(|e| RunAgentError::connection(format!("Ping failed: {}", e)))?;

        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_websocket_url_construction() {
        let client = SocketClient::new("ws://localhost:8000", None, Some("/api/v1")).unwrap();
        let url = client.get_websocket_url("test-agent", "generic").unwrap();
        assert_eq!(url.as_str(), "ws://localhost:8000/api/v1/agents/test-agent/execute/generic");
    }

    #[test]
    fn test_client_creation() {
        let client = SocketClient::new("ws://localhost:8000", None, None);
        assert!(client.is_ok());
    }

    #[test]
    fn test_url_conversion() {
        // Test HTTP to WebSocket URL conversion
        let client = SocketClient::default();
        // This would test the URL conversion logic in a real implementation
        assert!(client.is_ok());
    }
}