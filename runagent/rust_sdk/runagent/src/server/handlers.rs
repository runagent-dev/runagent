//! HTTP handlers for the local server

use crate::server::local_server::ServerState;
use crate::types::*;
use axum::{
    extract::{Path, State, WebSocketUpgrade},
    http::StatusCode,
    response::{IntoResponse, Json},
    extract::ws::{Message, WebSocket},
};
use chrono::Utc;
use futures::{sink::SinkExt, stream::StreamExt};
use serde_json::{json, Value};
use std::collections::HashMap;

/// Root endpoint showing server info
pub async fn root(State(state): State<ServerState>) -> impl IntoResponse {
    let info = AgentInfo {
        message: format!("RunAgent API - Agent {}", state.agent_id),
        version: crate::VERSION.to_string(),
        host: "127.0.0.1".to_string(),
        port: 8450, // Would be dynamic in real implementation
        config: {
            let mut config = HashMap::new();
            config.insert("agent_id".to_string(), json!(state.agent_id));
            config.insert("agent_path".to_string(), json!(state.agent_path));
            config.insert("framework".to_string(), json!("langchain"));
            config
        },
        endpoints: {
            let mut endpoints = HashMap::new();
            endpoints.insert("GET /".to_string(), "Agent info".to_string());
            endpoints.insert("GET /health".to_string(), "Health check".to_string());
            endpoints.insert("GET /api/v1/agents/{id}/architecture".to_string(), "Agent architecture".to_string());
            endpoints.insert("POST /api/v1/agents/{id}/execute/{entrypoint}".to_string(), "Run agent".to_string());
            endpoints.insert("WS /api/v1/agents/{id}/execute/{entrypoint}/ws".to_string(), "Stream agent".to_string());
            endpoints
        },
    };

    Json(info)
}

/// Health check endpoint
pub async fn health_check() -> impl IntoResponse {
    let health = json!({
        "status": "healthy",
        "server": "RunAgent Local Server",
        "timestamp": Utc::now().to_rfc3339(),
        "version": crate::VERSION
    });

    Json(health)
}

/// Get agent architecture
pub async fn get_agent_architecture(State(state): State<ServerState>) -> impl IntoResponse {
    // Load agent config or provide default architecture
    let architecture = json!({
        "agent_id": state.agent_id,
        "framework": "langchain",
        "entrypoints": [
            {
                "file": "main.py",
                "module": "run",
                "tag": "generic"
            },
            {
                "file": "main.py",
                "module": "run_stream", 
                "tag": "generic_stream"
            },
            {
                "file": "main.py",
                "module": "health_check",
                "tag": "health"
            }
        ]
    });

    Json(architecture)
}

/// Run agent endpoint
pub async fn run_agent(
    State(state): State<ServerState>,
    Path((_agent_id, entrypoint)): Path<(String, String)>,
    Json(request): Json<AgentRunRequest>,
) -> impl IntoResponse {
    let start_time = std::time::Instant::now();

    // Clone the input data to avoid borrow checker issues
    let input_kwargs = request.input_data.input_kwargs.clone();
    let input_args = request.input_data.input_args.clone();
    
    // Keep the original request data for serialization
    let input_data_json = serde_json::to_string(&request.input_data).unwrap_or_default();

    // Simple execution based on entrypoint
    let (success, output_data, error) = match entrypoint.as_str() {
        "generic" => execute_generic_entrypoint(&input_kwargs, &input_args),
        "health" => execute_health_entrypoint(),
        _ => (false, None, Some(format!("Unknown entrypoint: {}", entrypoint))),
    };

    let execution_time = start_time.elapsed().as_secs_f64();

    // Record the run in the database if available
    #[cfg(feature = "db")]
    if let Some(ref db_service) = state.db_service {
        let agent_run = crate::db::models::AgentRun {
            id: 0, // Will be set by database
            agent_id: state.agent_id.clone(),
            input_data: input_data_json,
            output_data: output_data.as_ref().map(|v| serde_json::to_string(v).unwrap_or_default()),
            success,
            error_message: error.clone(),
            execution_time: Some(execution_time),
            started_at: Utc::now(),
            completed_at: Some(Utc::now()),
        };

        let _ = db_service.record_agent_run(agent_run).await;
    }

    let response = AgentRunResponse {
        success,
        output_data,
        error,
        execution_time: Some(execution_time),
        agent_id: state.agent_id.clone(),
    };

    Json(response)
}

/// Execute generic entrypoint
fn execute_generic_entrypoint(
    input_kwargs: &HashMap<String, Value>,
    input_args: &[Value],
) -> (bool, Option<Value>, Option<String>) {
    // Extract message from kwargs or args
    let message = input_kwargs
        .get("message")
        .and_then(|v| v.as_str())
        .or_else(|| input_args.first().and_then(|v| v.as_str()))
        .unwrap_or("Hello from RunAgent!");

    let temperature = input_kwargs
        .get("temperature")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.7);

    let model = input_kwargs
        .get("model")
        .and_then(|v| v.as_str())
        .unwrap_or("gpt-3.5-turbo");

    // Create mock response
    let output = json!({
        "success": true,
        "response": format!("Mock LangChain response to: {}", message),
        "input": {
            "message": message,
            "temperature": temperature,
            "model": model
        },
        "metadata": {
            "timestamp": Utc::now().to_rfc3339(),
            "framework": "langchain",
            "agent_type": "test_mock",
            "model_used": model,
            "response_length": message.len() + 25,
            "mock": true
        }
    });

    (true, Some(output), None)
}

/// Execute health entrypoint
fn execute_health_entrypoint() -> (bool, Option<Value>, Option<String>) {
    let output = json!({
        "status": "healthy",
        "framework": "langchain",
        "agent_type": "test",
        "timestamp": Utc::now().to_rfc3339(),
        "environment": {
            "server": "rust",
            "version": crate::VERSION
        }
    });

    (true, Some(output), None)
}

/// WebSocket handler for streaming
pub async fn websocket_handler(
    ws: WebSocketUpgrade,
    State(state): State<ServerState>,
    Path((_agent_id, entrypoint)): Path<(String, String)>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_websocket(socket, state, entrypoint))
}

/// Handle WebSocket connection
async fn handle_websocket(socket: WebSocket, _state: ServerState, entrypoint: String) {
    let (mut sender, mut receiver) = socket.split();

    // Handle incoming messages
    while let Some(msg) = receiver.next().await {
        match msg {
            Ok(Message::Text(text)) => {
                // Parse the incoming message
                if let Ok(request) = serde_json::from_str::<Value>(&text) {
                    // Extract message from request
                    let message = request
                        .get("input_data")
                        .and_then(|d| d.get("input_kwargs"))
                        .and_then(|k| k.get("message"))
                        .and_then(|m| m.as_str())
                        .unwrap_or("Hello from streaming agent");

                    // Mock streaming response based on entrypoint
                    let chunks = match entrypoint.as_str() {
                        "generic_stream" => create_mock_stream_chunks(message),
                        _ => vec![
                            json!({
                                "type": "error",
                                "error": format!("Unsupported streaming entrypoint: {}", entrypoint),
                                "timestamp": Utc::now().to_rfc3339()
                            })
                        ],
                    };

                    // Send chunks
                    for (_i, chunk) in chunks.iter().enumerate() {
                        if sender
                            .send(Message::Text(chunk.to_string()))
                            .await
                            .is_err()
                        {
                            break;
                        }

                        // Small delay to simulate processing
                        tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;

                        // Break on completion chunk
                        if chunk.get("type").and_then(|t| t.as_str()) == Some("complete") {
                            break;
                        }
                    }
                }
            }
            Ok(Message::Close(_)) => {
                break;
            }
            _ => {}
        }
    }
}

/// Create mock streaming chunks
fn create_mock_stream_chunks(message: &str) -> Vec<Value> {
    let response_text = format!("Mock streaming response to: {}", message);
    let words: Vec<&str> = response_text.split_whitespace().collect();

    let mut chunks = Vec::new();

    // Add content chunks
    for (i, word) in words.iter().enumerate() {
        chunks.push(json!({
            "chunk_id": i + 1,
            "content": format!("{} ", word),
            "type": "content",
            "framework": "langchain",
            "mock": true,
            "timestamp": Utc::now().to_rfc3339()
        }));
    }

    // Add completion chunk
    chunks.push(json!({
        "type": "complete",
        "total_chunks": words.len(),
        "framework": "langchain",
        "mock": true,
        "timestamp": Utc::now().to_rfc3339()
    }));

    chunks
}

/// Error handler
pub async fn handle_error(err: Box<dyn std::error::Error + Send + Sync>) -> impl IntoResponse {
    let error_response = json!({
        "error": "Internal server error",
        "message": err.to_string(),
        "timestamp": Utc::now().to_rfc3339()
    });

    (StatusCode::INTERNAL_SERVER_ERROR, Json(error_response))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check() {
        let response = health_check().await;
        // In a real test, we'd assert the response content
        assert!(true); // Placeholder assertion
    }

    #[test]
    fn test_execute_generic_entrypoint() {
        let mut kwargs = HashMap::new();
        kwargs.insert("message".to_string(), json!("test message"));
        
        let (success, output, error) = execute_generic_entrypoint(&kwargs, &[]);
        assert!(success);
        assert!(output.is_some());
        assert!(error.is_none());
    }

    #[test]
    fn test_execute_health_entrypoint() {
        let (success, output, error) = execute_health_entrypoint();
        assert!(success);
        assert!(output.is_some());
        assert!(error.is_none());
    }
}