//! Simplified Database manager without migrations

use crate::constants::LOCAL_CACHE_DIRECTORY;
use crate::types::{RunAgentError, RunAgentResult};
use sqlx::{sqlite::SqliteConnectOptions, Pool, Sqlite, SqlitePool};
use std::path::PathBuf;

/// Database manager for SQLite operations (No migrations needed)
pub struct DatabaseManager {
    pool: Pool<Sqlite>,
    db_path: PathBuf,
}

impl DatabaseManager {
    /// Create a new database manager with automatic schema creation
    pub async fn new(db_path: Option<PathBuf>) -> RunAgentResult<Self> {
        let db_path = db_path.unwrap_or_else(|| {
            LOCAL_CACHE_DIRECTORY.join("runagent_local.db")
        });

        // Ensure parent directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| RunAgentError::database(format!("Failed to create database directory: {}", e)))?;
        }

        // Create connection options
        let options = SqliteConnectOptions::new()
            .filename(&db_path)
            .create_if_missing(true);

        // Create connection pool
        let pool = SqlitePool::connect_with(options).await
            .map_err(|e| RunAgentError::database(format!("Failed to connect to database: {}", e)))?;

        let manager = Self { pool, db_path };
        
        // Create tables if they don't exist
        manager.create_tables_if_not_exist().await?;

        Ok(manager)
    }

    /// Create tables if they don't exist (replaces migrations)
    async fn create_tables_if_not_exist(&self) -> RunAgentResult<()> {
        // Create agents table
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                agent_path TEXT NOT NULL,
                host TEXT NOT NULL DEFAULT 'localhost',
                port INTEGER NOT NULL DEFAULT 8450,
                framework TEXT,
                status TEXT NOT NULL DEFAULT 'deployed',
                deployed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_run DATETIME,
                run_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            "#
        )
        .execute(&self.pool)
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to create agents table: {}", e)))?;

        // Create agent_runs table
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                input_data TEXT NOT NULL,
                output_data TEXT,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                execution_time REAL,
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
            "#
        )
        .execute(&self.pool)
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to create agent_runs table: {}", e)))?;

        // Create indexes
        sqlx::query("CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)")
            .execute(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to create index: {}", e)))?;

        sqlx::query("CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs(agent_id)")
            .execute(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to create index: {}", e)))?;

        sqlx::query("CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs(started_at)")
            .execute(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to create index: {}", e)))?;

        Ok(())
    }

    /// Get the database pool
    pub fn pool(&self) -> &Pool<Sqlite> {
        &self.pool
    }

    /// Get the database path
    pub fn db_path(&self) -> &PathBuf {
        &self.db_path
    }

    /// Close the database connection
    pub async fn close(self) {
        self.pool.close().await;
    }
}