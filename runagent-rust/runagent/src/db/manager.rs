//! Simplified Database manager without migrations

use crate::constants::LOCAL_CACHE_DIRECTORY;
use crate::types::{RunAgentError, RunAgentResult};
use crate::db::models::DatabaseStats;
use sqlx::{sqlite::SqliteConnectOptions, Pool, Sqlite, SqlitePool, Transaction, Row};
use std::collections::HashMap;
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

    /// Execute a transaction
    pub async fn transaction<F, Fut, T>(&self, f: F) -> RunAgentResult<T>
    where
        F: FnOnce(&mut Transaction<'_, Sqlite>) -> Fut,
        Fut: std::future::Future<Output = RunAgentResult<T>>,
    {
        let mut tx = self.pool.begin().await
            .map_err(|e| RunAgentError::database(format!("Failed to begin transaction: {}", e)))?;
        
        let result = f(&mut tx).await?;
        
        tx.commit().await
            .map_err(|e| RunAgentError::database(format!("Failed to commit transaction: {}", e)))?;
        
        Ok(result)
    }

    /// Get database statistics
    pub async fn get_stats(&self) -> RunAgentResult<DatabaseStats> {
        // Get total agents
        let total_agents: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM agents")
            .fetch_one(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to count agents: {}", e)))?;

        // Get agent status counts
        let rows = sqlx::query("SELECT status, COUNT(*) as count FROM agents GROUP BY status")
            .fetch_all(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to get status counts: {}", e)))?;

        let mut agent_status_counts = HashMap::new();
        for row in rows {
            let status: String = row.get("status");
            let count: i64 = row.get("count");
            agent_status_counts.insert(status, count as usize);
        }

        // Get total runs (handle case where table might not exist or be empty)
        let total_runs: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM agent_runs")
            .fetch_optional(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to count runs: {}", e)))?
            .unwrap_or(0);

        // Calculate database size (approximate)
        let database_size_mb = match std::fs::metadata(&self.db_path) {
            Ok(metadata) => metadata.len() as f64 / (1024.0 * 1024.0),
            Err(_) => 0.0,
        };

        Ok(DatabaseStats {
            total_agents: total_agents as usize,
            agent_status_counts,
            total_runs: total_runs as usize,
            database_size_mb,
            database_path: self.db_path.to_string_lossy().to_string(),
            rest_client_configured: false, // This would be set by the service layer
        })
    }

    /// Get database file size in bytes
    pub fn get_database_size(&self) -> u64 {
        std::fs::metadata(&self.db_path)
            .map(|metadata| metadata.len())
            .unwrap_or(0)
    }

    /// Check if database file exists
    pub fn database_exists(&self) -> bool {
        self.db_path.exists()
    }

    /// Get database connection info
    pub fn get_connection_info(&self) -> HashMap<String, serde_json::Value> {
        let mut info = HashMap::new();
        info.insert("database_path".to_string(), serde_json::json!(self.db_path.to_string_lossy()));
        info.insert("database_exists".to_string(), serde_json::json!(self.database_exists()));
        info.insert("database_size_bytes".to_string(), serde_json::json!(self.get_database_size()));
        info.insert("pool_size".to_string(), serde_json::json!(self.pool.size()));
        info.insert("idle_connections".to_string(), serde_json::json!(self.pool.num_idle()));
        info
    }

    /// Perform database maintenance
    pub async fn maintenance(&self) -> RunAgentResult<()> {
        // Vacuum the database to reclaim space
        sqlx::query("VACUUM")
            .execute(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to vacuum database: {}", e)))?;

        // Analyze to update statistics
        sqlx::query("ANALYZE")
            .execute(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to analyze database: {}", e)))?;

        Ok(())
    }

    /// Check database integrity
    pub async fn check_integrity(&self) -> RunAgentResult<bool> {
        let result: String = sqlx::query_scalar("PRAGMA integrity_check")
            .fetch_one(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to check integrity: {}", e)))?;

        Ok(result == "ok")
    }

    /// Close the database connection
    pub async fn close(self) {
        self.pool.close().await;
    }
}

impl Drop for DatabaseManager {
    fn drop(&mut self) {
        // Note: We can't call async close() in Drop, but the pool will be cleaned up automatically
        tracing::debug!("DatabaseManager dropped for path: {}", self.db_path.display());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_database_manager_creation() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let manager = DatabaseManager::new(Some(db_path.clone())).await;
        assert!(manager.is_ok());
        
        let manager = manager.unwrap();
        assert_eq!(manager.db_path(), &db_path);
        assert!(manager.database_exists());
    }

    #[tokio::test]
    async fn test_database_stats() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let manager = DatabaseManager::new(Some(db_path)).await.unwrap();
        let stats = manager.get_stats().await;
        
        assert!(stats.is_ok());
        let stats = stats.unwrap();
        assert_eq!(stats.total_agents, 0);
        assert_eq!(stats.total_runs, 0);
    }

    #[tokio::test]
    async fn test_database_integrity() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let manager = DatabaseManager::new(Some(db_path)).await.unwrap();
        let integrity_ok = manager.check_integrity().await;
        
        assert!(integrity_ok.is_ok());
        assert!(integrity_ok.unwrap());
    }

    // #[tokio::test]
    // async fn test_transaction() {
    //     let temp_dir = TempDir::new().unwrap();
    //     let db_path = temp_dir.path().join("test.db");
        
    //     let manager = DatabaseManager::new(Some(db_path)).await.unwrap();
        
    //     let result = manager.transaction(|tx| async move {
    //         // Insert a test agent in transaction
    //         sqlx::query(
    //             "INSERT INTO agents (agent_id, agent_path) VALUES (?, ?)"
    //         )
    //         .bind("test-agent")
    //         .bind("/test/path")
    //         .execute(tx)
    //         .await
    //         .map_err(|e| RunAgentError::database(format!("Insert failed: {}", e)))?;
            
    //         Ok(42)
    //     }).await;
        
    //     assert!(result.is_ok());
    //     assert_eq!(result.unwrap(), 42);
        
    //     // Verify the agent was inserted
    //     let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM agents WHERE agent_id = ?")
    //         .bind("test-agent")
    //         .fetch_one(manager.pool())
    //         .await
    //         .unwrap();
        
    //     assert_eq!(count, 1);
    // }
}