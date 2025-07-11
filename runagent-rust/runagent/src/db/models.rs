//! Database models for the RunAgent SDK

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

/// Agent model representing deployed agents
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct Agent {
    pub agent_id: String,
    pub agent_path: String,
    pub host: String,
    pub port: i32,
    pub framework: Option<String>,
    pub status: String,
    pub deployed_at: DateTime<Utc>,
    pub last_run: Option<DateTime<Utc>>,
    pub run_count: i64,
    pub success_count: i64,
    pub error_count: i64,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Default for Agent {
    fn default() -> Self {
        let now = Utc::now();
        Self {
            agent_id: String::new(),
            agent_path: String::new(),
            host: "localhost".to_string(),
            port: 8450,
            framework: None,
            status: "deployed".to_string(),
            deployed_at: now,
            last_run: None,
            run_count: 0,
            success_count: 0,
            error_count: 0,
            created_at: now,
            updated_at: now,
        }
    }
}

impl Agent {
    /// Create a new Agent instance
    pub fn new(agent_id: String, agent_path: String, host: String, port: u16) -> Self {
        let now = Utc::now();
        Self {
            agent_id,
            agent_path,
            host,
            port: port as i32,
            framework: None,
            status: "deployed".to_string(),
            deployed_at: now,
            last_run: None,
            run_count: 0,
            success_count: 0,
            error_count: 0,
            created_at: now,
            updated_at: now,
        }
    }

    /// Set the framework for this agent
    pub fn with_framework(mut self, framework: String) -> Self {
        self.framework = Some(framework);
        self
    }

    /// Set the status for this agent
    pub fn with_status(mut self, status: String) -> Self {
        self.status = status;
        self
    }

    /// Update the agent's updated_at timestamp
    pub fn touch(&mut self) {
        self.updated_at = Utc::now();
    }

    /// Increment run count and update last_run
    pub fn record_run(&mut self, success: bool) {
        self.run_count += 1;
        self.last_run = Some(Utc::now());
        self.updated_at = Utc::now();
        
        if success {
            self.success_count += 1;
        } else {
            self.error_count += 1;
        }
    }

    /// Get success rate as percentage
    pub fn success_rate(&self) -> f64 {
        if self.run_count == 0 {
            0.0
        } else {
            (self.success_count as f64 / self.run_count as f64) * 100.0
        }
    }

    /// Check if the agent is healthy
    pub fn is_healthy(&self) -> bool {
        self.status == "deployed" && self.error_count < self.success_count * 2
    }
}

/// Agent run model representing individual executions
#[derive(Debug, Clone, FromRow, Serialize, Deserialize)]
pub struct AgentRun {
    pub id: i64,
    pub agent_id: String,
    pub input_data: String, // JSON string
    pub output_data: Option<String>, // JSON string
    pub success: bool,
    pub error_message: Option<String>,
    pub execution_time: Option<f64>,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
}

impl AgentRun {
    /// Create a new AgentRun instance
    pub fn new(agent_id: String, input_data: String) -> Self {
        Self {
            id: 0, // Will be set by the database
            agent_id,
            input_data,
            output_data: None,
            success: false,
            error_message: None,
            execution_time: None,
            started_at: Utc::now(),
            completed_at: None,
        }
    }

    /// Mark the run as completed successfully
    pub fn complete_success(mut self, output_data: String, execution_time: f64) -> Self {
        self.output_data = Some(output_data);
        self.success = true;
        self.execution_time = Some(execution_time);
        self.completed_at = Some(Utc::now());
        self
    }

    /// Mark the run as completed with error
    pub fn complete_error(mut self, error_message: String, execution_time: f64) -> Self {
        self.error_message = Some(error_message);
        self.success = false;
        self.execution_time = Some(execution_time);
        self.completed_at = Some(Utc::now());
        self
    }

    /// Get the duration of this run
    pub fn duration(&self) -> Option<chrono::Duration> {
        self.completed_at.map(|completed| completed - self.started_at)
    }
}

/// Database capacity information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapacityInfo {
    pub current_count: usize,
    pub max_capacity: usize,
    pub default_limit: usize,
    pub remaining_slots: Option<usize>,
    pub is_full: bool,
    pub agents: Vec<AgentSummary>,
    pub oldest_agent: Option<AgentSummary>,
    pub newest_agent: Option<AgentSummary>,
    pub limit_info: LimitInfo,
    pub rest_client_configured: bool,
}

/// Agent summary for capacity info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentSummary {
    pub agent_id: String,
    pub deployed_at: DateTime<Utc>,
    pub framework: Option<String>,
    pub status: String,
    pub host: String,
    pub port: i32,
}

impl From<Agent> for AgentSummary {
    fn from(agent: Agent) -> Self {
        Self {
            agent_id: agent.agent_id,
            deployed_at: agent.deployed_at,
            framework: agent.framework,
            status: agent.status,
            host: agent.host,
            port: agent.port,
        }
    }
}

/// Limit information from API or default
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LimitInfo {
    pub limit: usize,
    pub enhanced: bool,
    pub source: String, // "default", "api", "enhanced"
    pub api_available: bool,
    pub api_validated: bool,
    pub tier_info: Option<serde_json::Value>,
    pub features: Vec<String>,
    pub expires_at: Option<String>,
    pub unlimited: bool,
    pub error: Option<String>,
}

impl Default for LimitInfo {
    fn default() -> Self {
        Self {
            limit: 5,
            enhanced: false,
            source: "default".to_string(),
            api_available: false,
            api_validated: false,
            tier_info: None,
            features: Vec::new(),
            expires_at: None,
            unlimited: false,
            error: None,
        }
    }
}

/// Database statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseStats {
    pub total_agents: usize,
    pub agent_status_counts: std::collections::HashMap<String, usize>,
    pub total_runs: usize,
    pub database_size_mb: f64,
    pub database_path: String,
    pub rest_client_configured: bool,
}

/// Agent deployment information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeploymentInfo {
    pub agent_id: String,
    pub host: String,
    pub port: u16,
    pub status: String,
    pub framework: String,
    pub deployed_at: DateTime<Utc>,
    pub exists: bool,
    pub source_exists: bool,
    pub deployment_path: String,
    pub folder_path: String,
    pub stats: AgentStats,
}

/// Agent statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStats {
    pub total_runs: i64,
    pub success_count: i64,
    pub error_count: i64,
    pub success_rate: f64,
    pub last_run: Option<DateTime<Utc>>,
    pub avg_execution_time: Option<f64>,
}

impl From<Agent> for AgentStats {
    fn from(agent: Agent) -> Self {
        Self {
            total_runs: agent.run_count,
            success_count: agent.success_count,
            error_count: agent.error_count,
            success_rate: agent.success_rate(),
            last_run: agent.last_run,
            avg_execution_time: None, // Would be calculated from runs
        }
    }
}

/// Add operation result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddAgentResult {
    pub success: bool,
    pub message: String,
    pub current_count: usize,
    pub limit_source: String,
    pub api_check_performed: bool,
    pub allocated_host: Option<String>,
    pub allocated_port: Option<u16>,
    pub address: Option<String>,
    pub max_allowed: Option<usize>,
    pub remaining_slots: Option<String>, // Can be "unlimited"
    pub limit_info: Option<LimitInfo>,
    pub error: Option<String>,
    pub code: Option<String>,
    pub oldest_agent: Option<AgentSummary>,
    pub suggestion: Option<String>,
}

impl AddAgentResult {
    pub fn success(
        message: String,
        current_count: usize,
        limit_source: String,
        api_check_performed: bool,
    ) -> Self {
        Self {
            success: true,
            message,
            current_count,
            limit_source,
            api_check_performed,
            allocated_host: None,
            allocated_port: None,
            address: None,
            max_allowed: None,
            remaining_slots: None,
            limit_info: None,
            error: None,
            code: None,
            oldest_agent: None,
            suggestion: None,
        }
    }

    pub fn error(error: String, code: String) -> Self {
        Self {
            success: false,
            message: String::new(),
            current_count: 0,
            limit_source: String::new(),
            api_check_performed: false,
            allocated_host: None,
            allocated_port: None,
            address: None,
            max_allowed: None,
            remaining_slots: None,
            limit_info: None,
            error: Some(error),
            code: Some(code),
            oldest_agent: None,
            suggestion: None,
        }
    }

    pub fn with_allocation(mut self, host: String, port: u16) -> Self {
        self.allocated_host = Some(host.clone());
        self.allocated_port = Some(port);
        self.address = Some(format!("{}:{}", host, port));
        self
    }

    pub fn with_capacity_info(mut self, max_allowed: usize, remaining_slots: usize) -> Self {
        self.max_allowed = Some(max_allowed);
        self.remaining_slots = Some(if max_allowed == 999 {
            "unlimited".to_string()
        } else {
            remaining_slots.to_string()
        });
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_creation() {
        let agent = Agent::new(
            "test-agent".to_string(),
            "/path/to/agent".to_string(),
            "localhost".to_string(),
            8450,
        );

        assert_eq!(agent.agent_id, "test-agent");
        assert_eq!(agent.agent_path, "/path/to/agent");
        assert_eq!(agent.host, "localhost");
        assert_eq!(agent.port, 8450);
        assert_eq!(agent.status, "deployed");
        assert_eq!(agent.run_count, 0);
    }

    #[test]
    fn test_agent_with_framework() {
        let agent = Agent::new(
            "test-agent".to_string(),
            "/path/to/agent".to_string(),
            "localhost".to_string(),
            8450,
        ).with_framework("langchain".to_string());

        assert_eq!(agent.framework, Some("langchain".to_string()));
    }

    #[test]
    fn test_agent_record_run() {
        let mut agent = Agent::new(
            "test-agent".to_string(),
            "/path/to/agent".to_string(),
            "localhost".to_string(),
            8450,
        );

        assert_eq!(agent.run_count, 0);
        assert_eq!(agent.success_count, 0);

        agent.record_run(true);
        assert_eq!(agent.run_count, 1);
        assert_eq!(agent.success_count, 1);
        assert_eq!(agent.error_count, 0);
        assert!(agent.last_run.is_some());
    }


    #[test]
    fn test_agent_run_creation() {
        let run = AgentRun::new(
            "test-agent".to_string(),
            r#"{"message": "test"}"#.to_string(),
        );

        assert_eq!(run.agent_id, "test-agent");
        assert!(!run.success);
        assert!(run.output_data.is_none());
        assert!(run.completed_at.is_none());
    }

    #[test]
    fn test_agent_run_completion() {
        let run = AgentRun::new(
            "test-agent".to_string(),
            r#"{"message": "test"}"#.to_string(),
        ).complete_success(
            r#"{"response": "Hello"}"#.to_string(),
            1.5,
        );

        assert!(run.success);
        assert!(run.output_data.is_some());
        assert!(run.completed_at.is_some());
        assert_eq!(run.execution_time, Some(1.5));
    }

    #[test]
    fn test_add_agent_result() {
        let result = AddAgentResult::success(
            "Agent added".to_string(),
            1,
            "default".to_string(),
            false,
        ).with_allocation("localhost".to_string(), 8450);

        assert!(result.success);
        assert_eq!(result.allocated_host, Some("localhost".to_string()));
        assert_eq!(result.allocated_port, Some(8450));
        assert_eq!(result.address, Some("localhost:8450".to_string()));
    }

    #[test]
    fn test_agent_summary_from_agent() {
        let agent = Agent::new(
            "test-agent".to_string(),
            "/path/to/agent".to_string(),
            "localhost".to_string(),
            8450,
        ).with_framework("langchain".to_string());

        let summary = AgentSummary::from(agent.clone());
        assert_eq!(summary.agent_id, agent.agent_id);
        assert_eq!(summary.framework, agent.framework);
        assert_eq!(summary.status, agent.status);
    }
}