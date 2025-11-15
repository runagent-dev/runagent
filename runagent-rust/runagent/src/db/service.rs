//! Database service for agent lookups

use crate::types::{RunAgentError, RunAgentResult};
use once_cell::sync::Lazy;
use sqlx::{sqlite::SqlitePool, Row};
use std::path::PathBuf;

/// Database file name
const DATABASE_FILE_NAME: &str = "runagent_local.db";

/// Environment variable for cache directory
const ENV_LOCAL_CACHE_DIRECTORY: &str = "RUNAGENT_CACHE_DIR";

/// Local cache directory (computed at runtime)
static LOCAL_CACHE_DIRECTORY: Lazy<PathBuf> = Lazy::new(|| {
    // Check environment variable first
    if let Ok(env_path) = std::env::var(ENV_LOCAL_CACHE_DIRECTORY) {
        return PathBuf::from(env_path);
    }
    
    // Default to ~/.runagent
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".runagent")
});

/// Agent information stored in database
#[derive(Debug, Clone)]
pub struct AgentInfo {
    pub agent_id: String,
    pub agent_path: String,
    pub host: String,
    pub port: i32,
    pub framework: Option<String>,
    pub status: Option<String>,
}

/// Minimal database service for agent lookups
pub struct DatabaseService {
    pool: SqlitePool,
}

impl DatabaseService {
    /// Create a new database service
    pub async fn new(db_path: Option<PathBuf>) -> RunAgentResult<Self> {
        let db_path = db_path.unwrap_or_else(|| {
            LOCAL_CACHE_DIRECTORY.join(DATABASE_FILE_NAME)
        });

        // Ensure directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| RunAgentError::database(format!("Failed to create db directory: {}", e)))?;
        }

        let database_url = format!("sqlite:{}", db_path.display());
        
        let pool = SqlitePool::connect(&database_url).await
            .map_err(|e| RunAgentError::database(format!("Failed to connect to database: {}", e)))?;

        // Initialize database schema
        Self::init_schema(&pool).await?;

        Ok(Self { pool })
    }

    /// Initialize database schema
    async fn init_schema(pool: &SqlitePool) -> RunAgentResult<()> {
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                agent_path TEXT NOT NULL,
                host TEXT NOT NULL DEFAULT 'localhost',
                port INTEGER NOT NULL DEFAULT 8450,
                framework TEXT,
                status TEXT DEFAULT 'deployed',
                is_local INTEGER DEFAULT 1,
                fingerprint TEXT,
                deployed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            "#,
        )
        .execute(pool)
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to create schema: {}", e)))?;

        Ok(())
    }

    /// Get agent by ID
    pub async fn get_agent(&self, agent_id: &str) -> RunAgentResult<Option<AgentInfo>> {
        let row = sqlx::query(
            "SELECT agent_id, agent_path, host, port, framework, status FROM agents WHERE agent_id = ?"
        )
        .bind(agent_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to query agent: {}", e)))?;

        if let Some(row) = row {
            Ok(Some(AgentInfo {
                agent_id: row.get("agent_id"),
                agent_path: row.get("agent_path"),
                host: row.get("host"),
                port: row.get("port"),
                framework: row.get::<Option<String>, _>("framework"),
                status: row.get::<Option<String>, _>("status"),
            }))
        } else {
            Ok(None)
        }
    }

    /// Get agent address (host, port) by ID
    pub async fn get_agent_address(&self, agent_id: &str) -> RunAgentResult<Option<(String, u16)>> {
        if let Some(agent) = self.get_agent(agent_id).await? {
            Ok(Some((agent.host, agent.port as u16)))
        } else {
            Ok(None)
        }
    }
}

impl Drop for DatabaseService {
    fn drop(&mut self) {
        // Note: sqlx pool handles cleanup automatically
    }
}

