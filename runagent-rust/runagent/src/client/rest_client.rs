//! REST client for HTTP API interactions

use crate::types::{RunAgentError, RunAgentResult};
use crate::utils::config::Config;
use reqwest::{Client, Method, Response};
use serde_json::Value;
use std::collections::HashMap;
use std::time::Duration;
use url::Url;

/// REST client for API interactions
pub struct RestClient {
    client: Client,
    base_url: String,
    api_key: Option<String>,
    api_prefix: String,
}

impl RestClient {
    /// Create a new REST client with custom configuration
    pub fn new(
        base_url: &str,
        api_key: Option<String>,
        api_prefix: Option<&str>,
    ) -> RunAgentResult<Self> {
        // Increase timeout to 10 minutes (600 seconds) to match agent execution timeout
        let client = Client::builder()
            .timeout(Duration::from_secs(600))
            .user_agent("RunAgent-Rust-SDK/0.1.0")
            .build()?;

        let base_url = base_url.trim_end_matches('/').to_string();
        let api_prefix = api_prefix.unwrap_or("/api/v1").to_string();

        Ok(Self {
            client,
            base_url,
            api_key,
            api_prefix,
        })
    }

    /// Create a default REST client using configuration
    pub fn default() -> RunAgentResult<Self> {
        let config = Config::load()?;
        Self::new(
            &config.base_url(),
            config.api_key(),
            Some("/api/v1"),
        )
    }

    fn get_url(&self, path: &str) -> RunAgentResult<Url> {
        let path = path.strip_prefix('/').unwrap_or(path);
        let full_path = format!("{}{}/{}", self.base_url, self.api_prefix, path);
        Url::parse(&full_path).map_err(|e| RunAgentError::validation(format!("Invalid URL: {}", e)))
    }

    async fn handle_response(&self, response: Response) -> RunAgentResult<Value> {
        let status = response.status();
        
        if status.is_success() {
            let json: Value = response.json().await?;
            Ok(json)
        } else {
            let error_text = response.text().await?;
            let error_msg = if error_text.is_empty() {
                format!("HTTP Error: {}", status)
            } else {
                // Try to parse as JSON to get error details
                if let Ok(json) = serde_json::from_str::<Value>(&error_text) {
                    // Try to extract nested error message
                    if let Some(error_obj) = json.get("error") {
                        if let Some(message) = error_obj.get("message").and_then(|m| m.as_str()) {
                            message.to_string()
                        } else if let Some(detail) = json.get("detail").and_then(|d| d.as_str()) {
                            detail.to_string()
                        } else if let Some(message) = json.get("message").and_then(|m| m.as_str()) {
                            message.to_string()
                        } else if let Some(error) = json.get("error").and_then(|e| e.as_str()) {
                            error.to_string()
                        } else {
                            error_text
                        }
                    } else if let Some(detail) = json.get("detail").and_then(|d| d.as_str()) {
                        detail.to_string()
                    } else if let Some(message) = json.get("message").and_then(|m| m.as_str()) {
                        message.to_string()
                    } else if let Some(error) = json.get("error").and_then(|e| e.as_str()) {
                        error.to_string()
                    } else {
                        error_text
                    }
                } else {
                    error_text
                }
            };

            // Check if error message contains permission/403 info even if status is 500
            if error_msg.contains("permission") || error_msg.contains("403") || error_msg.contains("do not have permission") {
                return Err(RunAgentError::authentication(format!(
                    "Access denied: {}. This usually means:\n  - The agent doesn't belong to your account\n  - Your API key doesn't have permission to access this agent\n  - The agent ID is incorrect", error_msg
                )));
            }
            
            match status.as_u16() {
                401 => Err(RunAgentError::authentication(error_msg)),
                403 => Err(RunAgentError::authentication(format!(
                    "Access denied: {}. This usually means:\n  - The agent doesn't belong to your account\n  - Your API key doesn't have permission to access this agent\n  - The agent ID is incorrect", error_msg
                ))),
                400 | 422 => Err(RunAgentError::validation(error_msg)),
                404 => Err(RunAgentError::validation(format!("Not found: {}", error_msg))),
                500..=599 => Err(RunAgentError::server(format!("Server error: {}", error_msg))),
                _ => Err(RunAgentError::connection(error_msg)),
            }
        }
    }

    async fn request(
        &self,
        method: Method,
        path: &str,
        data: Option<&Value>,
        params: Option<&HashMap<String, String>>,
    ) -> RunAgentResult<Value> {
        let mut url = self.get_url(path)?;
        
        // Add API key as token query parameter if available (matching WebSocket behavior)
        if let Some(ref api_key) = self.api_key {
            url.query_pairs_mut()
                .append_pair("token", api_key);
        }
        
        let mut request_builder = self.client.request(method, url);

        // Add query parameters
        if let Some(params) = params {
            request_builder = request_builder.query(params);
        }

        // Add JSON body for POST/PUT requests
        if let Some(data) = data {
            request_builder = request_builder
                .header("Content-Type", "application/json")
                .json(data);
        }

        // Add Authorization header if API key is available
        if let Some(ref api_key) = self.api_key {
            request_builder = request_builder.header("Authorization", format!("Bearer {}", api_key));
        }

        let response = request_builder.send().await?;
        self.handle_response(response).await
    }

    /// Send a GET request
    pub async fn get(&self, path: &str) -> RunAgentResult<Value> {
        self.get_with_params(path, None).await
    }

    /// Send a GET request with query parameters
    pub async fn get_with_params(
        &self,
        path: &str,
        params: Option<&HashMap<String, String>>,
    ) -> RunAgentResult<Value> {
        self.request(Method::GET, path, None, params).await
    }

    /// Send a POST request
    pub async fn post(&self, path: &str, data: &Value) -> RunAgentResult<Value> {
        self.request(Method::POST, path, Some(data), None).await
    }

    /// Send a PUT request
    pub async fn put(&self, path: &str, data: &Value) -> RunAgentResult<Value> {
        self.request(Method::PUT, path, Some(data), None).await
    }

    /// Send a DELETE request
    pub async fn delete(&self, path: &str) -> RunAgentResult<Value> {
        self.request(Method::DELETE, path, None, None).await
    }

    /// Run an agent via REST API
    pub async fn run_agent(
        &self,
        agent_id: &str,
        entrypoint_tag: &str,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        let data = serde_json::json!({
            "id": "run_start",
            "entrypoint_tag": entrypoint_tag,
            "input_args": input_args,
            "input_kwargs": input_kwargs,
            "timeout_seconds": 600,
            "async_execution": false
        });

        let path = format!("agents/{}/run", agent_id);
        let url = self.get_url(&path)?;
        tracing::debug!("Running agent {} with entrypoint {} at {}", agent_id, entrypoint_tag, url);
        
        self.post(&path, &data).await
            .map_err(|e| {
                if e.category() == "validation" && e.to_string().contains("Not found") {
                    RunAgentError::validation(format!(
                        "Agent {} not found on server at {}. Check that:\n  - The agent exists and is deployed\n  - The agent ID is correct\n  - The base URL ({}) is correct\n  - Your API key is valid (if required)",
                        agent_id, url, self.base_url
                    ))
                } else {
                    e
                }
            })
    }

    /// Get agent architecture information
    pub async fn get_agent_architecture(&self, agent_id: &str) -> RunAgentResult<Value> {
        let path = format!("agents/{}/architecture", agent_id);
        let url = self.get_url(&path)?;
        tracing::debug!("Fetching agent architecture for {} at {}", agent_id, url);
        let response = self.get(&path).await
            .map_err(|e| {
                if e.category() == "validation" && e.to_string().contains("Not found") {
                    RunAgentError::validation(format!(
                        "Agent {} not found at {}. Check that:\n  - The agent ID is correct\n  - The agent exists and is deployed\n  - Your API key has access to this agent\n  - The base URL ({}) is correct",
                        agent_id, url, self.base_url
                    ))
                } else {
                    e
                }
            })?;

        if let Some(success) = response.get("success").and_then(|v| v.as_bool()) {
            if success {
                if let Some(data) = response.get("data") {
                    return Ok(data.clone());
                }
                return Err(RunAgentError::execution(
                    "ARCHITECTURE_MISSING",
                    "Architecture response missing data",
                    Some("Redeploy the agent or ensure entrypoints are configured.".to_string()),
                    Some(response),
                ));
            }

            let (code, message, suggestion) = if let Some(error_obj) = response.get("error") {
                if let Some(obj) = error_obj.as_object() {
                    (
                        obj.get("code")
                            .and_then(|c| c.as_str())
                            .unwrap_or("UNKNOWN_ERROR")
                            .to_string(),
                        obj.get("message")
                            .and_then(|m| m.as_str())
                            .unwrap_or("Failed to retrieve agent architecture")
                            .to_string(),
                        obj.get("suggestion")
                            .and_then(|s| s.as_str())
                            .map(|s| s.to_string()),
                    )
                } else if let Some(msg) = error_obj.as_str() {
                    ("UNKNOWN_ERROR".to_string(), msg.to_string(), None)
                } else {
                    ("UNKNOWN_ERROR".to_string(), "Failed to retrieve agent architecture".to_string(), None)
                }
            } else {
                (
                    "UNKNOWN_ERROR".to_string(),
                    response
                        .get("message")
                        .and_then(|m| m.as_str())
                        .unwrap_or("Failed to retrieve agent architecture")
                        .to_string(),
                    None,
                )
            };

            return Err(RunAgentError::execution(
                code,
                message,
                suggestion,
                Some(response),
            ));
        }

        Ok(response)
    }

    /// Health check
    pub async fn health_check(&self) -> RunAgentResult<Value> {
        self.get("health").await
    }

    /// Validate API connection
    pub async fn validate_api_connection(&self) -> RunAgentResult<Value> {
        match self.health_check().await {
                    Ok(_response) => {
                        let mut result = serde_json::json!({
                            "success": true,
                            "api_connected": true,
                            "base_url": self.base_url
                        });

                        if self.api_key.is_some() {
                            // Test authentication if API key is provided
                            match self.get_local_db_limits().await {
                                Ok(limits_result) => {
                                    result["api_authenticated"] = limits_result.get("api_validated").unwrap_or(&Value::Bool(false)).clone();
                                    result["enhanced_limits"] = limits_result.get("enhanced_limits").unwrap_or(&Value::Bool(false)).clone();
                                }
                                Err(_) => {
                                    result["api_authenticated"] = Value::Bool(false);
                                    result["enhanced_limits"] = Value::Bool(false);
                                }
                            }
                        } else {
                            result["api_authenticated"] = Value::Bool(false);
                            result["enhanced_limits"] = Value::Bool(false);
                            result["message"] = Value::String("No API key provided".to_string());
                        }

                        Ok(result)
                    }
                    Err(e) => Ok(serde_json::json!({
                        "success": false,
                        "api_connected": false,
                        "error": format!("API health check failed: {}", e)
                    })),
                }
    }

    /// Get local database limits from backend API
    pub async fn get_local_db_limits(&self) -> RunAgentResult<Value> {
        if self.api_key.is_none() {
            return Ok(serde_json::json!({
                "success": false,
                "error": "No API key provided",
                "default_limit": 5,
                "current_limit": 5,
                "has_api_key": false,
                "enhanced_limits": false
            }));
        }

        tracing::info!("Checking API limits...");

        match self.get("limits/agents").await {
            Ok(response) => {
                let max_agents = response.get("max_agents").and_then(|v| v.as_i64()).unwrap_or(5);
                let enhanced = max_agents > 5;
                let unlimited = max_agents == -1;

                if enhanced {
                    tracing::info!("Enhanced limits active: {} agents", if unlimited { "unlimited".to_string() } else { max_agents.to_string() });
                }

                Ok(serde_json::json!({
                    "success": true,
                    "max_agents": if unlimited { 999 } else { max_agents },
                    "current_limit": if unlimited { 999 } else { max_agents },
                    "default_limit": 5,
                    "has_api_key": true,
                    "enhanced_limits": enhanced,
                    "tier_info": response.get("tier_info").unwrap_or(&Value::Null),
                    "features": response.get("features").unwrap_or(&Value::Array(vec![])),
                    "expires_at": response.get("expires_at").unwrap_or(&Value::Null),
                    "unlimited": unlimited,
                    "api_validated": true
                }))
            }
            Err(e) => {
                let error_msg = if e.category() == "authentication" {
                    "API key invalid or expired - using default limits"
                } else {
                    "API connection failed - using default limits"
                };

                tracing::warn!("{}", error_msg);

                Ok(serde_json::json!({
                    "success": false,
                    "error": format!("{}", e),
                    "default_limit": 5,
                    "current_limit": 5,
                    "has_api_key": true,
                    "enhanced_limits": false,
                    "api_validated": false
                }))
            }
        }
    }

    /// Upload agent to remote server
    pub async fn upload_agent(
        &self,
        folder_path: &str,
        metadata: Option<&HashMap<String, Value>>,
    ) -> RunAgentResult<Value> {
        // This would implement file upload functionality
        // For now, return a placeholder
        let _folder_path = folder_path;
        let _metadata = metadata;
        
        Err(RunAgentError::generic("Upload functionality not yet implemented"))
    }

    /// Start a remote agent
    pub async fn start_agent(
        &self,
        agent_id: &str,
        config: Option<&HashMap<String, Value>>,
    ) -> RunAgentResult<Value> {
        let data = config.cloned().unwrap_or_default();
        let path = format!("agents/{}/start", agent_id);
        self.post(&path, &serde_json::json!(data)).await
    }

    /// Get agent status
    pub async fn get_agent_status(&self, agent_id: &str) -> RunAgentResult<Value> {
        let path = format!("agents/{}/status", agent_id);
        self.get(&path).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_url_construction() {
        let client = RestClient::new("http://localhost:8000", None, Some("/api/v1")).unwrap();
        let url = client.get_url("agents/test").unwrap();
        assert_eq!(url.as_str(), "http://localhost:8000/api/v1/agents/test");
    }

    #[test]
    fn test_url_construction_with_leading_slash() {
        let client = RestClient::new("http://localhost:8000", None, Some("/api/v1")).unwrap();
        let url = client.get_url("/agents/test").unwrap();
        assert_eq!(url.as_str(), "http://localhost:8000/api/v1/agents/test");
    }

    #[test]
    fn test_client_creation() {
        let client = RestClient::new("http://localhost:8000", None, None);
        assert!(client.is_ok());
    }
}