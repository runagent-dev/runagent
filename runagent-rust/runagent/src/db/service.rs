//! High-level database service with business logic

use crate::client::RestClient;
use crate::db::{manager::DatabaseManager, models::*};
use crate::types::{RunAgentError, RunAgentResult};
use chrono::{DateTime, Duration, Utc};
use sqlx::{Row, FromRow};
// use std::collections::HashMap;
use std::path::PathBuf;

/// High-level database service with business logic
pub struct DatabaseService {
    manager: DatabaseManager,
    rest_client: Option<RestClient>,
    limits_cache: Option<LimitInfo>,
    cache_expiry: Option<DateTime<Utc>>,
}

impl DatabaseService {
    /// Create a new database service
    pub async fn new(db_path: Option<PathBuf>) -> RunAgentResult<Self> {
        let manager = DatabaseManager::new(db_path).await?;
        
        Ok(Self {
            manager,
            rest_client: None,
            limits_cache: None,
            cache_expiry: None,
        })
    }

    /// Create database service with REST client for enhanced limits
    pub async fn with_rest_client(
        db_path: Option<PathBuf>,
        rest_client: RestClient,
    ) -> RunAgentResult<Self> {
        let manager = DatabaseManager::new(db_path).await?;
        
        Ok(Self {
            manager,
            rest_client: Some(rest_client),
            limits_cache: None,
            cache_expiry: None,
        })
    }

    /// Add a new agent to the database
    pub async fn add_agent(&self, agent: Agent) -> RunAgentResult<AddAgentResult> {
        let current_count = self.get_agent_count().await?;
        let default_limit = self.get_default_limit();

        // Phase 1: Check if we're within default limits
        if current_count < default_limit {
            let agent_id = agent.agent_id.clone();

            self.insert_agent(agent.clone()).await?;
            
            return Ok(AddAgentResult::success(
                format!("Agent {} added successfully", agent_id),
                current_count + 1,
                "default".to_string(),
                false,
            ));
        }

        // Phase 2: Check enhanced limits via API
        if let Some(limit_info) = self.check_enhanced_limits().await? {
            if current_count >= limit_info.limit {
                let _oldest_agent = self.get_oldest_agent().await?;
                
                return Ok(AddAgentResult::error(
                    format!("Maximum {} agents allowed", limit_info.limit),
                    "DATABASE_FULL".to_string(),
                ).with_capacity_info(limit_info.limit, limit_info.limit.saturating_sub(current_count)));
            }

            self.insert_agent(agent.clone()).await?;
            
            return Ok(AddAgentResult::success(
                format!("Agent added with enhanced limits"),
                current_count + 1,
                if limit_info.enhanced { "enhanced" } else { "default" }.to_string(),
                true,
            ).with_capacity_info(limit_info.limit, limit_info.limit.saturating_sub(current_count + 1)));
        }

        // Fallback: Use default limits
        if current_count >= default_limit {
            return Ok(AddAgentResult::error(
                format!("Maximum {} agents allowed", default_limit),
                "DATABASE_FULL".to_string(),
            ));
        }

        self.insert_agent(agent.clone()).await?;
        Ok(AddAgentResult::success(
            "Agent added successfully".to_string(),
            current_count + 1,
            "default".to_string(),
            false,
        ))
    }

    /// Get an agent by ID
    pub async fn get_agent(&self, agent_id: &str) -> RunAgentResult<Option<Agent>> {
        let row = sqlx::query("SELECT * FROM agents WHERE agent_id = ?")
            .bind(agent_id)
            .fetch_optional(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to get agent: {}", e)))?;

        if let Some(row) = row {
            Ok(Some(Agent::from_row(&row)?))
        } else {
            Ok(None)
        }
    }

    /// List all agents
    pub async fn list_agents(&self) -> RunAgentResult<Vec<Agent>> {
        let rows = sqlx::query("SELECT * FROM agents ORDER BY deployed_at DESC")
            .fetch_all(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to list agents: {}", e)))?;

        let mut agents = Vec::new();
        for row in rows {
            agents.push(Agent::from_row(&row)?);
        }

        Ok(agents)
    }

    /// Update agent status
    pub async fn update_agent_status(&self, agent_id: &str, status: &str) -> RunAgentResult<bool> {
        let result = sqlx::query("UPDATE agents SET status = ?, updated_at = ? WHERE agent_id = ?")
            .bind(status)
            .bind(Utc::now())
            .bind(agent_id)
            .execute(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to update agent status: {}", e)))?;

        Ok(result.rows_affected() > 0)
    }

    /// Replace an existing agent
    pub async fn replace_agent(
        &self,
        old_agent_id: &str,
        new_agent: Agent,
    ) -> RunAgentResult<bool> {
        // Use a transaction to ensure atomicity
        let mut tx = self.manager.pool().begin().await
            .map_err(|e| RunAgentError::database(format!("Failed to begin transaction: {}", e)))?;
        
        // Delete old agent
        sqlx::query("DELETE FROM agents WHERE agent_id = ?")
            .bind(old_agent_id)
            .execute(&mut *tx)
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to delete old agent: {}", e)))?;

        // Insert new agent
        sqlx::query(
            "INSERT INTO agents (agent_id, agent_path, host, port, framework, status, deployed_at, created_at, updated_at) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        .bind(&new_agent.agent_id)
        .bind(&new_agent.agent_path)
        .bind(&new_agent.host)
        .bind(new_agent.port)
        .bind(&new_agent.framework)
        .bind(&new_agent.status)
        .bind(new_agent.deployed_at)
        .bind(new_agent.created_at)
        .bind(new_agent.updated_at)
        .execute(&mut *tx)
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to insert new agent: {}", e)))?;

        // Commit transaction
        tx.commit().await
            .map_err(|e| RunAgentError::database(format!("Failed to commit transaction: {}", e)))?;

        Ok(true)
    }

    /// Record an agent run
    pub async fn record_agent_run(&self, run: AgentRun) -> RunAgentResult<i64> {
        let result = sqlx::query(
            "INSERT INTO agent_runs (agent_id, input_data, output_data, success, error_message, execution_time, started_at, completed_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
             RETURNING id"
        )
        .bind(&run.agent_id)
        .bind(&run.input_data)
        .bind(&run.output_data)
        .bind(run.success)
        .bind(&run.error_message)
        .bind(run.execution_time)
        .bind(run.started_at)
        .bind(run.completed_at)
        .fetch_one(self.manager.pool())
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to record agent run: {}", e)))?;

        let run_id: i64 = result.get(0);

        // Update agent statistics
        self.update_agent_stats(&run.agent_id, run.success, run.execution_time).await?;

        Ok(run_id)
    }

    /// Get capacity information
    pub async fn get_capacity_info(&self) -> RunAgentResult<CapacityInfo> {
        let current_count = self.get_agent_count().await?;
        let default_limit = self.get_default_limit();
        
        let limit_info = self.check_enhanced_limits().await?.unwrap_or_else(|| LimitInfo {
            limit: default_limit,
            enhanced: false,
            source: "default".to_string(),
            ..Default::default()
        });

        let agents = self.list_agents().await?;
        let agent_summaries: Vec<AgentSummary> = agents.into_iter().map(|a| a.into()).collect();

        Ok(CapacityInfo {
            current_count,
            max_capacity: limit_info.limit,
            default_limit,
            remaining_slots: if limit_info.unlimited {
                None
            } else {
                Some(limit_info.limit.saturating_sub(current_count))
            },
            is_full: current_count >= limit_info.limit,
            agents: agent_summaries.clone(),
            oldest_agent: agent_summaries.first().cloned(),
            newest_agent: agent_summaries.last().cloned(),
            limit_info,
            rest_client_configured: self.rest_client.is_some(),
        })
    }

    /// Cleanup old runs
    pub async fn cleanup_old_runs(&self, days_old: i32) -> RunAgentResult<usize> {
        let cutoff_date = Utc::now() - Duration::days(days_old as i64);
        
        let result = sqlx::query("DELETE FROM agent_runs WHERE started_at < ?")
            .bind(cutoff_date)
            .execute(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to cleanup old runs: {}", e)))?;

        Ok(result.rows_affected() as usize)
    }

    /// Get database statistics
    pub async fn get_stats(&self) -> RunAgentResult<DatabaseStats> {
        self.manager.get_stats().await
    }

    // Private helper methods

    async fn insert_agent(&self, agent: Agent) -> RunAgentResult<()> {
        sqlx::query(
            "INSERT INTO agents (agent_id, agent_path, host, port, framework, status, deployed_at, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        .bind(&agent.agent_id)
        .bind(&agent.agent_path)
        .bind(&agent.host)
        .bind(agent.port)
        .bind(&agent.framework)
        .bind(&agent.status)
        .bind(agent.deployed_at)
        .bind(agent.created_at)
        .bind(agent.updated_at)
        .execute(self.manager.pool())
        .await
        .map_err(|e| RunAgentError::database(format!("Failed to insert agent: {}", e)))?;

        Ok(())
    }

    async fn get_agent_count(&self) -> RunAgentResult<usize> {
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM agents")
            .fetch_one(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to get agent count: {}", e)))?;

        Ok(count as usize)
    }

    async fn get_oldest_agent(&self) -> RunAgentResult<Option<AgentSummary>> {
        let row = sqlx::query("SELECT * FROM agents ORDER BY deployed_at ASC LIMIT 1")
            .fetch_optional(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to get oldest agent: {}", e)))?;

        if let Some(row) = row {
            let agent = Agent::from_row(&row)?;
            Ok(Some(agent.into()))
        } else {
            Ok(None)
        }
    }

    async fn update_agent_stats(
        &self,
        agent_id: &str,
        success: bool,
        _execution_time: Option<f64>,
    ) -> RunAgentResult<()> {
        let mut query_str = "UPDATE agents SET run_count = run_count + 1, last_run = ?, updated_at = ?".to_string();

        if success {
            query_str.push_str(", success_count = success_count + 1");
        } else {
            query_str.push_str(", error_count = error_count + 1");
        }

        query_str.push_str(" WHERE agent_id = ?");

        sqlx::query(&query_str)
            .bind(Utc::now())
            .bind(Utc::now())
            .bind(agent_id)
            .execute(self.manager.pool())
            .await
            .map_err(|e| RunAgentError::database(format!("Failed to update agent stats: {}", e)))?;

        Ok(())
    }

    async fn check_enhanced_limits(&self) -> RunAgentResult<Option<LimitInfo>> {
        // Check cache first
        if let (Some(limits), Some(expiry)) = (&self.limits_cache, &self.cache_expiry) {
            if Utc::now() < *expiry {
                return Ok(Some(limits.clone()));
            }
        }

        if let Some(rest_client) = &self.rest_client {
            match rest_client.get_local_db_limits().await {
                Ok(response) => {
                    if response.get("success").and_then(|v| v.as_bool()).unwrap_or(false) {
                        let max_agents = response.get("max_agents").and_then(|v| v.as_i64()).unwrap_or(5) as usize;
                        let enhanced = response.get("enhanced_limits").and_then(|v| v.as_bool()).unwrap_or(false);
                        let unlimited = max_agents == 999;

                        let limit_info = LimitInfo {
                            limit: max_agents,
                            enhanced,
                            source: if enhanced { "api" } else { "default" }.to_string(),
                            api_available: true,
                            api_validated: response.get("api_validated").and_then(|v| v.as_bool()).unwrap_or(false),
                            tier_info: response.get("tier_info").cloned(),
                            features: response.get("features")
                                .and_then(|v| v.as_array())
                                .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
                                .unwrap_or_default(),
                            expires_at: response.get("expires_at").and_then(|v| v.as_str()).map(|s| s.to_string()),
                            unlimited,
                            error: None,
                        };

                        // Cache for 5 minutes
                        // Note: In a real implementation, we'd need to handle mutable self properly
                        
                        return Ok(Some(limit_info));
                    }
                }
                Err(_) => {
                    // API call failed, use default limits
                }
            }
        }

        Ok(None)
    }

    fn get_default_limit(&self) -> usize {
        5 // Default limit from constants
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[tokio::test]
    async fn test_database_service_creation() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let service = DatabaseService::new(Some(db_path)).await;
        assert!(service.is_ok());
    }

    #[tokio::test]
    async fn test_add_agent() {
        let temp_dir = TempDir::new().unwrap();
        let db_path = temp_dir.path().join("test.db");
        
        let service = DatabaseService::new(Some(db_path)).await.unwrap();
        
        let agent = Agent::new(
            "test-agent".to_string(),
            "/path/to/agent".to_string(),
            "localhost".to_string(),
            8450,
        );
        
        let result = service.add_agent(agent).await;
        assert!(result.is_ok());
    }
}