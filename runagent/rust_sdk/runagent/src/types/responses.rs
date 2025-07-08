//! Response types for API interactions

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Generic API response wrapper
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
    pub message: Option<String>,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

impl<T> ApiResponse<T> {
    pub fn success(data: T) -> Self {
        Self {
            success: true,
            data: Some(data),
            error: None,
            message: None,
            metadata: None,
        }
    }

    pub fn error<E: Into<String>>(error: E) -> Self {
        Self {
            success: false,
            data: None,
            error: Some(error.into()),
            message: None,
            metadata: None,
        }
    }

    pub fn with_message<M: Into<String>>(mut self, message: M) -> Self {
        self.message = Some(message.into());
        self
    }

    pub fn with_metadata(mut self, metadata: HashMap<String, serde_json::Value>) -> Self {
        self.metadata = Some(metadata);
        self
    }
}

/// Response for agent execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResponse {
    pub output: serde_json::Value,
    pub execution_time: f64,
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Response for streaming execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamChunk {
    pub chunk_id: String,
    pub data: serde_json::Value,
    pub is_final: bool,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

/// Response for database operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseResponse {
    pub affected_rows: usize,
    pub last_insert_id: Option<i64>,
    pub operation: String,
}

/// Response for template operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateResponse {
    pub templates: HashMap<String, Vec<String>>,
    pub total_count: usize,
}

/// Response for template info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateInfoResponse {
    pub framework: String,
    pub template: String,
    pub description: Option<String>,
    pub files: Vec<String>,
    pub directories: Vec<String>,
    pub metadata: Option<HashMap<String, serde_json::Value>>,
}

/// Response for agent deployment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeploymentResponse {
    pub agent_id: String,
    pub host: String,
    pub port: u16,
    pub endpoint: String,
    pub status: String,
}

/// Response for agent status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusResponse {
    pub agent_id: String,
    pub status: String,
    pub framework: String,
    pub last_updated: String,
    pub statistics: HashMap<String, serde_json::Value>,
}

/// Response for health check
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub uptime: f64,
    pub timestamp: String,
    pub services: HashMap<String, String>,
}

/// Response for configuration status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigStatusResponse {
    pub configured: bool,
    pub api_key_set: bool,
    pub base_url: String,
    pub user_info: HashMap<String, serde_json::Value>,
}

/// Response for validation operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResponse {
    pub valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
    pub suggestions: Vec<String>,
}

/// Paginated response wrapper
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedResponse<T> {
    pub items: Vec<T>,
    pub total: usize,
    pub page: usize,
    pub per_page: usize,
    pub has_next: bool,
    pub has_prev: bool,
}

impl<T> PaginatedResponse<T> {
    pub fn new(items: Vec<T>, total: usize, page: usize, per_page: usize) -> Self {
        let has_next = (page * per_page) < total;
        let has_prev = page > 1;

        Self {
            items,
            total,
            page,
            per_page,
            has_next,
            has_prev,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_api_response_success() {
        let response = ApiResponse::success("test data");
        assert!(response.success);
        assert_eq!(response.data, Some("test data"));
        assert!(response.error.is_none());
    }

    #[test]
    fn test_api_response_error() {
        let response: ApiResponse<String> = ApiResponse::error("Something went wrong");
        assert!(!response.success);
        assert!(response.data.is_none());
        assert_eq!(response.error, Some("Something went wrong".to_string()));
    }

    #[test]
    fn test_api_response_with_message() {
        let response = ApiResponse::success("data")
            .with_message("Operation completed successfully");
        assert!(response.success);
        assert_eq!(response.message, Some("Operation completed successfully".to_string()));
    }

    #[test]
    fn test_paginated_response() {
        let items = vec!["item1", "item2", "item3"];
        let response = PaginatedResponse::new(items, 10, 1, 5);
        
        assert_eq!(response.total, 10);
        assert_eq!(response.page, 1);
        assert_eq!(response.per_page, 5);
        assert!(response.has_next);
        assert!(!response.has_prev);
    }

    #[test]
    fn test_stream_chunk() {
        let chunk = StreamChunk {
            chunk_id: "chunk-1".to_string(),
            data: serde_json::json!({"content": "Hello"}),
            is_final: false,
            metadata: None,
        };

        assert_eq!(chunk.chunk_id, "chunk-1");
        assert!(!chunk.is_final);
    }
}