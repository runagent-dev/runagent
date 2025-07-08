//! Database manager for SQLite operations

use crate::constants::LOCAL_CACHE_DIRECTORY;
use crate::types::{RunAgentError, RunAgentResult};
use sqlx::{migrate::MigrateDatabase, Pool, Sqlite, SqlitePool};
use std::path::PathBuf;

/// Database manager for SQLite operations
pub struct DatabaseManager {
    pool: Pool<Sqlite>,
    db_path: PathBuf,
}

impl DatabaseManager {
    /// Create a new database manager
    pub async fn new(db_path: Option<PathBuf>) -> RunAgentResult<Self> {
        let db_path = db_path.unwrap_or_else(|| {
            LOCAL_CACHE_DIRECTORY.join("runagent_local.db")
        });

        // Ensure parent directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| RunAgentError::database(format!("Failed to create database directory: {}", e)))?;
        }

        let database_url = format!("sqlite://{}", db_path.to_string_lossy());

        // Create database if it doesn't exist
        if !Sqlite::database_exists(&database_url).await.unwrap_or(false) {
            Sqlite::create_database(&database_url).await
                .map_err(|e| RunAgentError::database(format!("Failed to create database: {}", e)))?;
        }

        // Create connection pool
        let pool = SqlitePool::connect(&database_url).await
            .map_err(|e| RunAgentError::database(format!("Failed to connect to database: {}", e)))?;

        // Run migrations
        sqlx::migrate!("./migrations").run(&pool).await
            .map_err(|e| RunAgentError::database(format!("Failed to run migrations: {}", e)))?;

        Ok(Self { pool, db_path })
    }

    /// Get the database pool
    pub fn pool(&self) -> &Pool<Sqlite> {
        &self.pool
    }

    /// Get the database path
    pub fn db_path(&self) -> &PathBuf {
        &self.db_path
    }

    /// Check if database is initialized
    pub async fn is_initialized(&self) -> bool {
        // Try to query a simple table to check if database is working
        sqlx::query("SELECT 1")
            .fetch_optional(&self.pool)
            .await
            .is_ok()
    }

    /// Get database size in bytes
    pub async fn get_size(&self) -> RunAgentResult<u64> {
        if self.db_path.exists() {
            let metadata = std::fs::metadata(&self.db_path)
                .map_err(|e| RunAgentError::database(format!("Failed to get database size: {}", e)))?;
            Ok(metadata.len())
        } else {
            Ok(0)
        }
    }

    /// Close the database connection
    pub async fn close(self) {
        self.pool.close().await;
    }

    /// Execute a transaction
    pub async fn transaction<F, R>(&self, f: F) -> RunAgentResult<R>
    where
        F: for<'c> FnOnce(&'c mut sqlx::Transaction<'_, Sqlite>) -> futures::future::BoxFuture<'c, RunAgentResult<R>> + Send,
        R: Send,
    {
        let mut tx = self.pool.begin().await
            .map_err(|e| RunAgentError::database(format!("Failed to begin transaction: {}", e)))?;

        let result = f(&mut tx).await;

        match result {
            Ok(value) => {
                tx.commit().await
                    .map_err(|e| RunAgentError::database(format!("Failed to commit transaction: {}", e)))?;
                Ok(value)
            }
            Err(err) => {
                tx.rollback().await
                    .map_err(|e| RunAgentError::database(format!("Failed to rollback transaction: {}", e)))?;
                Err(err)
            }
        }
    }

    /// Vacuum the database to reclaim space
    pub async fn vacuum(&self) -> RunAgentResult<()> {
        sqlx::query("VACUUM")
            .execute(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to vacuum database: {}", e)))?;
        Ok(())
    }

    /// Get database statistics
    pub async fn get_stats(&self) -> RunAgentResult<DatabaseStats> {
        let agent_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM agents")
            .fetch_one(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to get agent count: {}", e)))?;

        let run_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM agent_runs")
            .fetch_one(&self.pool)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to get run count: {}", e)))?;

        let db_size = self.get_size().await?;

        Ok(DatabaseStats {
            total_agents: agent_count as usize,
            total_runs: run_count as usize,
            database_size_mb: db_size as f64 / 1024.0 / 1024.0,
            database_path: self.db_path.to_string_lossy().to_string(),
            agent_status_counts: std::collections::HashMap::new(), // Would be populated in a real implementation
            rest_client_configured: false, // Would be determined based on configuration
        })
    }
}

/// Database statistics
#[derive(Debug, Clone)]
pub struct DatabaseStats {
    /// Total number of agents
    pub total_agents: usize,
    /// Total number of runs
    pub total_runs: usize,
    /// Database size in MB
    pub database_size_mb: f64,
    /// Path to database file
    pub database_path: String,
    /// Count of agents by status
    pub agent_status_counts: std::collections::HashMap<String, usize>,
    /// Whether REST client is configured
    pub rest_client_configured: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_database_manager_creation() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let manager = DatabaseManager::new(Some(db_path)).await;
        assert!(manager.is_ok());
    }

    #[tokio::test]
    async fn test_database_initialization() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let manager = DatabaseManager::new(Some(db_path)).await.unwrap();
        assert!(manager.is_initialized().await);
    }
}