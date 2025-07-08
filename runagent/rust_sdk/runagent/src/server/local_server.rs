//! Local FastAPI-like server for testing deployed agents

use crate::db::DatabaseService;
use crate::server::handlers;
use crate::types::{RunAgentError, RunAgentResult};
use axum::{
    // Remove unused State import
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::net::TcpListener;
use tower::ServiceBuilder;
use tower_http::{
    cors::CorsLayer,
    trace::TraceLayer,
};

/// Shared server state
#[derive(Clone)]
pub struct ServerState {
    pub agent_id: String,
    pub agent_path: PathBuf,
    pub db_service: Arc<DatabaseService>,
}

/// Local server for testing deployed agents
pub struct LocalServer {
    app: Router,
    addr: SocketAddr,
    state: ServerState,
}

impl LocalServer {
    /// Create a new local server
    pub async fn new(
        agent_id: String,
        agent_path: PathBuf,
        host: &str,
        port: u16,
    ) -> RunAgentResult<Self> {
        let addr = format!("{}:{}", host, port)
            .parse()
            .map_err(|e| RunAgentError::config(format!("Invalid address: {}", e)))?;

        // Initialize database service
        let db_service = Arc::new(DatabaseService::new(None).await?);

        let state = ServerState {
            agent_id,
            agent_path,
            db_service,
        };

        let app = Self::create_router(state.clone());

        Ok(Self { app, addr, state })
    }

    /// Create a new local server from agent path with auto-discovery
    pub async fn from_path(
        agent_path: PathBuf,
        host: Option<&str>,
        port: Option<u16>,
    ) -> RunAgentResult<Self> {
        let host = host.unwrap_or("127.0.0.1");
        let port = port.unwrap_or(8450);

        // Auto-generate agent ID
        let agent_id = uuid::Uuid::new_v4().to_string();

        Self::new(agent_id, agent_path, host, port).await
    }

    /// Create the Axum router with all routes
    fn create_router(state: ServerState) -> Router {
        Router::new()
            // API routes
            .route("/api/v1", get(handlers::root))
            .route("/api/v1/health", get(handlers::health_check))
            .route(
                &format!("/api/v1/agents/{}/architecture", state.agent_id),
                get(handlers::get_agent_architecture),
            )
            .route(
                &format!("/api/v1/agents/{}/execute/:entrypoint", state.agent_id),
                post(handlers::run_agent),
            )
            // WebSocket routes
            .route(
                &format!("/api/v1/agents/{}/execute/:entrypoint/ws", state.agent_id),
                get(handlers::websocket_handler),
            )
            // State
            .with_state(state)
            // Middleware
            .layer(
                ServiceBuilder::new()
                    .layer(TraceLayer::new_for_http())
                    .layer(CorsLayer::permissive())
            )
    }

    /// Start the server
    pub async fn start(self) -> RunAgentResult<()> {
        tracing::info!("Starting local server on {}", self.addr);
        tracing::info!("Agent ID: {}", self.state.agent_id);
        tracing::info!("Agent Path: {}", self.state.agent_path.display());
        tracing::info!("API Docs: http://{}/docs", self.addr);

        let listener = TcpListener::bind(self.addr)
            .await
            .map_err(|e| RunAgentError::connection(format!("Failed to bind to {}: {}", self.addr, e)))?;

        axum::serve(listener, self.app)
            .await
            .map_err(|e| RunAgentError::server(format!("Server error: {}", e)))?;

        Ok(())
    }

    /// Get server information
    pub fn get_info(&self) -> ServerInfo {
        ServerInfo {
            agent_id: self.state.agent_id.clone(),
            agent_path: self.state.agent_path.clone(),
            host: self.addr.ip().to_string(),
            port: self.addr.port(),
            url: format!("http://{}", self.addr),
            docs_url: format!("http://{}/docs", self.addr),
            status: "running".to_string(),
        }
    }
}

/// Server information
#[derive(Debug, Clone)]
pub struct ServerInfo {
    pub agent_id: String,
    pub agent_path: PathBuf,
    pub host: String,
    pub port: u16,
    pub url: String,
    pub docs_url: String,
    pub status: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_local_server_creation() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path().join("agent");
        std::fs::create_dir_all(&agent_path).unwrap();

        let server = LocalServer::new(
            "test-agent".to_string(),
            agent_path,
            "127.0.0.1",
            8450,
        ).await;

        assert!(server.is_ok());
    }

    #[tokio::test]
    async fn test_server_from_path() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path().join("agent");
        std::fs::create_dir_all(&agent_path).unwrap();

        let server = LocalServer::from_path(agent_path, None, None).await;
        assert!(server.is_ok());
    }
}