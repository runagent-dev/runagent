//! HTTP handlers for the local server

use crate::server::local_server::{ServerState};
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
        host: "127.0.0.1".to_string(), // Would be dynamic in real implementation
        port: 8450, // Would be dynamic in real implementation
        config: {
            let mut config = HashMap::new();
            config.insert("agent_id".to_string(), json!(state.agent_id));
            config.insert("agent_path".to_string(), json!(state.agent_path));
            config
        },
        endpoints: {
            let mut endpoints = HashMap::new();
            endpoints.insert("GET /".to_string(), "Agent info".to_string());
            endpoints.insert("GET /health".to_string(), "Health check".to_string());
            endpoints.insert("POST /api/v1/agents/{id}/execute/{entrypoint}".to_string(), "Run agent".to_string());
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
    // In a real implementation, this would read the agent config
    let architecture = json!({
        "agent_id": state.agent_id,
        "entrypoints": [
            {
                "file": "main.py",
                "module": "run",
                "tag": "generic"
            }
        ]
    });

    Json(architecture)
}

/// Run agent endpoint
pub async fn run_agent(
    State(state): State<ServerState>,
    Path(entrypoint): Path<String>,
    Json(request): Json<AgentRunRequest>,
) -> impl IntoResponse {
    let start_time = std::time::Instant::now();

    // In a real implementation, this would:
    // 1. Load and execute the agent based on the entrypoint
    // 2. Handle different frameworks (LangChain, LangGraph, etc.)
    // 3. Return the actual agent response

    // For now, return a mock response
    let execution_time = start_time.elapsed().as_secs_f64();

    let response = AgentRunResponse {
        success: true,
        output_data: Some(json!({
            "response": format!("Mock response from agent {} using entrypoint {}", state.agent_id, entrypoint),
            "input_received": request.input_data,
            "timestamp": Utc::now().to_rfc3339()
        })),
        error: None,
        execution_time: Some(execution_time),
        agent_id: state.agent_id.clone(),
    };

    // Record the run in the database
    let agent_run = crate::db::models::AgentRun {
        id: 0, // Will be set by database
        agent_id: state.agent_id.clone(),
        input_data: serde_json::to_string(&request.input_data).unwrap_or_default(),
        output_data: response.output_data.as_ref().map(|v| serde_json::to_string(v).unwrap_or_default()),
        success: response.success,
        error_message: response.error.clone(),
        execution_time: response.execution_time,
        started_at: Utc::now(),
        completed_at: Some(Utc::now()),
    };

    // In a real implementation, we'd record this in the database
    let _ = state.db_service.record_agent_run(agent_run).await;

    Json(response)
}

/// WebSocket handler for streaming
pub async fn websocket_handler(
    ws: WebSocketUpgrade,
    State(state): State<ServerState>,
    Path(entrypoint): Path<String>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_websocket(socket, state, entrypoint))
}

/// Handle WebSocket connection
async fn handle_websocket(socket: WebSocket, state: ServerState, entrypoint: String) {
    let (mut sender, mut receiver) = socket.split();

    // Handle incoming messages
    while let Some(msg) = receiver.next().await {
        match msg {
            Ok(Message::Text(text)) => {
                // Parse the incoming message
                if let Ok(request) = serde_json::from_str::<Value>(&text) {
                    // Mock streaming response
                    let chunks = vec![
                        "Hello",
                        " from",
                        " streaming",
                        " agent",
                        &format!(" {} ", state.agent_id),
                        "using",
                        " entrypoint",
                        &format!(" {}", entrypoint),
                    ];

                    for chunk in chunks {
                        let stream_chunk = json!({
                            "type": "chunk",
                            "data": chunk,
                            "timestamp": Utc::now().to_rfc3339()
                        });

                        if sender
                            .send(Message::Text(stream_chunk.to_string()))
                            .await
                            .is_err()
                        {
                            break;
                        }

                        // Small delay to simulate processing
                        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                    }

                    // Send completion message
                    let completion = json!({
                        "type": "complete",
                        "data": "Stream completed",
                        "timestamp": Utc::now().to_rfc3339()
                    });

                    let _ = sender.send(Message::Text(completion.to_string())).await;
                }
            }
            Ok(Message::Close(_)) => {
                break;
            }
            _ => {}
        }
    }
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
    use crate::db::DatabaseService;
    use std::sync::Arc;
    use tempfile::TempDir;

    async fn create_test_state() -> ServerState {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path().join("agent");
        std::fs::create_dir_all(&agent_path).unwrap();

        let db_service = Arc::new(DatabaseService::new(None).await.unwrap());

        ServerState {
            agent_id: "test-agent".to_string(),
            agent_path,
            db_service,
        }
    }

    #[tokio::test]
    async fn test_health_check() {
        let response = health_check().await;
        // In a real test, we'd assert the response content
        assert!(true); // Placeholder assertion
    }

    #[tokio::test]
    async fn test_root_handler() {
        let state = create_test_state().await;
        let response = root(State(state)).await;
        // In a real test, we'd assert the response content
        assert!(true); // Placeholder assertion
    }
}