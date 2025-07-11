//! Local FastAPI-like server for testing deployed agents

use crate::server::handlers;
use crate::types::{RunAgentError, RunAgentResult};
use axum::{
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

#[cfg(feature = "db")]
use crate::db::DatabaseService;

/// Shared server state
#[derive(Clone)]
pub struct ServerState {
    pub agent_id: String,
    pub agent_path: PathBuf,
    #[cfg(feature = "db")]
    pub db_service: Option<Arc<DatabaseService>>,
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

        // Initialize database service if feature is enabled
        #[cfg(feature = "db")]
        let db_service = match DatabaseService::new(None).await {
            Ok(service) => Some(Arc::new(service)),
            Err(e) => {
                tracing::warn!("Failed to initialize database service: {}", e);
                None
            }
        };

        let state = ServerState {
            agent_id: agent_id.clone(),
            agent_path,
            #[cfg(feature = "db")]
            db_service,
        };

        let app = Self::create_router(state.clone(), &agent_id);

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
    fn create_router(state: ServerState, agent_id: &str) -> Router {
        Router::new()
            // Root and health
            .route("/", get(handlers::root))
            .route("/health", get(handlers::health_check))
            
            // API routes
            .route("/api/v1", get(handlers::root))
            .route("/api/v1/health", get(handlers::health_check))
            .route(
                &format!("/api/v1/agents/{}/architecture", agent_id),
                get(handlers::get_agent_architecture),
            )
            .route(
                "/api/v1/agents/:agent_id/execute/:entrypoint",
                post(handlers::run_agent),
            )
            
            // WebSocket routes for streaming
            .route(
                "/api/v1/agents/:agent_id/execute/:entrypoint/ws",
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

        tracing::info!("🚀 Server ready at http://{}", self.addr);
        tracing::info!("🆔 Agent ID: {}", self.state.agent_id);
        tracing::info!("📁 Agent Path: {}", self.state.agent_path.display());

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

    /// Get the agent ID
    pub fn agent_id(&self) -> &str {
        &self.state.agent_id
    }

    /// Get the server address
    pub fn addr(&self) -> SocketAddr {
        self.addr
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
        
        if let Ok(server) = server {
            assert!(!server.agent_id().is_empty());
        }
    }
}