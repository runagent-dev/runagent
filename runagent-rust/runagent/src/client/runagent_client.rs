//! Main RunAgent client for interacting with deployed agents

use crate::client::rest_client::RestClient;
use crate::client::socket_client::SocketClient;
use crate::types::{RunAgentError, RunAgentResult};
use crate::utils::serializer::CoreSerializer;
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::pin::Pin;

#[cfg(feature = "db")]
use crate::db::DatabaseService;

/// Main client for interacting with RunAgent deployments
pub struct RunAgentClient {
    agent_id: String,
    entrypoint_tag: String,
    local: bool,
    rest_client: RestClient,
    socket_client: SocketClient,
    serializer: CoreSerializer,
    agent_architecture: Option<Value>,
    extra_params: Option<HashMap<String, Value>>,

    #[cfg(feature = "db")]
    #[allow(dead_code)] // Reserved for future use
    db_service: Option<DatabaseService>,
}

/// Configuration for creating a RunAgent client
/// 
/// All fields except `agent_id` and `entrypoint_tag` are optional.
/// 
/// # Direct Construction
/// 
/// ```rust,no_run
/// use runagent::{RunAgentClient, RunAgentClientConfig};
/// 
/// #[tokio::main]
/// async fn main() -> runagent::RunAgentResult<()> {
///     let client = RunAgentClient::new(RunAgentClientConfig {
///         agent_id: "agent-id".to_string(),
///         entrypoint_tag: "entrypoint".to_string(),
///         local: None,
///         host: None,
///         port: None,
///         api_key: Some("key".to_string()),
///         base_url: Some("http://localhost:8333/".to_string()),
///         extra_params: None,
///         enable_registry: None,
///     }).await?;
///     Ok(())
/// }
/// ```
/// 
/// # Builder Pattern (Alternative)
/// 
/// ```rust,no_run
/// use runagent::{RunAgentClient, RunAgentClientConfig};
/// use std::env;
/// 
/// #[tokio::main]
/// async fn main() -> runagent::RunAgentResult<()> {
///     let client = RunAgentClient::new(
///         RunAgentClientConfig::new("agent-id", "entrypoint")
///             .with_api_key(env::var("RUNAGENT_API_KEY").unwrap_or_else(|_| "key".to_string()))
///             .with_base_url("http://localhost:8333/")
///     ).await?;
///     Ok(())
/// }
/// ```
#[derive(Debug, Clone)]
pub struct RunAgentClientConfig {
    /// Agent ID (required)
    pub agent_id: String,
    /// Entrypoint tag (required)
    pub entrypoint_tag: String,
    /// Whether this is a local agent (default: false)
    pub local: Option<bool>,
    /// Host for local agents (optional, will lookup from DB if not provided and local=true)
    pub host: Option<String>,
    /// Port for local agents (optional, will lookup from DB if not provided and local=true)
    pub port: Option<u16>,
    /// API key for remote agents (optional, can also use RUNAGENT_API_KEY env var)
    pub api_key: Option<String>,
    /// Base URL for remote agents (optional, defaults to https://backend.run-agent.ai)
    pub base_url: Option<String>,
    /// Extra parameters for future use
    pub extra_params: Option<HashMap<String, Value>>,
    /// Enable database registry lookup (default: true for local agents)
    pub enable_registry: Option<bool>,
}

impl RunAgentClientConfig {
    /// Create a new config with required fields
    pub fn new(agent_id: impl Into<String>, entrypoint_tag: impl Into<String>) -> Self {
        Self {
            agent_id: agent_id.into(),
            entrypoint_tag: entrypoint_tag.into(),
            local: None,
            host: None,
            port: None,
            api_key: None,
            base_url: None,
            extra_params: None,
            enable_registry: None,
        }
    }

    /// Create a config with defaults for optional fields
    /// 
    /// This allows you to use `..RunAgentClientConfig::default()` syntax
    /// to omit None values when constructing directly.
    pub fn default() -> Self {
        Self {
            agent_id: String::new(), // Dummy - will be overridden
            entrypoint_tag: String::new(), // Dummy - will be overridden
            local: None,
            host: None,
            port: None,
            api_key: None,
            base_url: None,
            extra_params: None,
            enable_registry: None,
        }
    }

    /// Set local flag
    pub fn with_local(mut self, local: bool) -> Self {
        self.local = Some(local);
        self
    }

    /// Set host and port for local agents
    pub fn with_address(mut self, host: impl Into<String>, port: u16) -> Self {
        self.host = Some(host.into());
        self.port = Some(port);
        self
    }

    /// Set API key
    pub fn with_api_key(mut self, api_key: impl Into<String>) -> Self {
        self.api_key = Some(api_key.into());
        self
    }

    /// Set base URL
    pub fn with_base_url(mut self, base_url: impl Into<String>) -> Self {
        self.base_url = Some(base_url.into());
        self
    }

    /// Set extra parameters
    pub fn with_extra_params(mut self, extra_params: HashMap<String, Value>) -> Self {
        self.extra_params = Some(extra_params);
        self
    }

    /// Enable or disable registry lookup
    pub fn with_enable_registry(mut self, enable: bool) -> Self {
        self.enable_registry = Some(enable);
        self
    }
}

impl RunAgentClient {
    /// Create a new RunAgent client from configuration
    /// 
    /// This is the single entry point for creating clients.
    /// 
    /// # Examples
    /// 
    /// ```rust,no_run
    /// use runagent::{RunAgentClient, RunAgentClientConfig};
    /// use std::env;
    /// 
    /// #[tokio::main]
    /// async fn main() -> runagent::RunAgentResult<()> {
    ///     // Local agent with explicit address
    ///     let client = RunAgentClient::new(RunAgentClientConfig::new("agent-id", "entrypoint")
    ///         .with_local(true)
    ///         .with_address("127.0.0.1", 8450)
    ///         .with_enable_registry(false)
    ///     ).await?;
    ///     
    ///     // Remote agent
    ///     let client = RunAgentClient::new(RunAgentClientConfig::new("agent-id", "entrypoint")
    ///         .with_api_key(env::var("RUNAGENT_API_KEY").unwrap_or_else(|_| "key".to_string()))
    ///     ).await?;
    ///     Ok(())
    /// }
    /// ```
    pub async fn new(config: RunAgentClientConfig) -> RunAgentResult<Self> {
        use crate::constants::{DEFAULT_BASE_URL, ENV_RUNAGENT_API_KEY, ENV_RUNAGENT_BASE_URL};
        
        let local = config.local.unwrap_or(false);
        let enable_registry = config.enable_registry.unwrap_or(local);
        
        // Resolve host/port for local agents
        let (host, port) = if local {
            // If host/port provided, use them
            if let (Some(h), Some(p)) = (&config.host, &config.port) {
                (Some(h.clone()), Some(*p))
            } else if enable_registry {
                // Try database lookup if enabled
                #[cfg(feature = "db")]
                {
                    let db_service = DatabaseService::new(None).await?;
                    if let Some(agent_info) = db_service.get_agent(&config.agent_id).await? {
                        tracing::info!("🔍 Found agent in database: {}:{}", agent_info.host, agent_info.port);
                        (Some(agent_info.host), Some(agent_info.port as u16))
                    } else {
                        (config.host.clone(), config.port)
                    }
                }
                #[cfg(not(feature = "db"))]
                {
                    (config.host.clone(), config.port)
                }
            } else {
                (config.host.clone(), config.port)
            }
        } else {
            (None, None)
        };

        // Resolve API key (config > env var)
        let api_key = config.api_key.or_else(|| {
            std::env::var(ENV_RUNAGENT_API_KEY).ok()
        });

        // Resolve base URL (config > env var > default)
        let base_url = config.base_url.or_else(|| {
            std::env::var(ENV_RUNAGENT_BASE_URL).ok()
        }).unwrap_or_else(|| DEFAULT_BASE_URL.to_string());

        if !local {
            tracing::info!("🌐 Connecting to remote agent at {}", base_url);
            if api_key.is_some() {
                tracing::debug!("🔑 API key provided");
            } else {
                tracing::warn!("⚠️  No API key provided - using default limits");
            }
        }

        let serializer = CoreSerializer::new(10.0)?;
        #[cfg(feature = "db")]
        let db_service: Option<DatabaseService> = None;
        #[cfg(not(feature = "db"))]
        let db_service: Option<DatabaseService> = None;

        let (rest_client, socket_client) = if local {
            let host = host.ok_or_else(|| {
                RunAgentError::validation(
                    "Host is required for local clients. Provide host/port in config or enable registry for database lookup.",
                )
            })?;
            let port = port.ok_or_else(|| {
                RunAgentError::validation(
                    "Port is required for local clients. Provide host/port in config or enable registry for database lookup.",
                )
            })?;

            tracing::info!("🔌 Using address: {}:{}", host, port);

            let agent_base_url = format!("http://{}:{}", host, port);
            let agent_socket_url = format!("ws://{}:{}", host, port);

            let rest_client = RestClient::new(&agent_base_url, None, Some("/api/v1"))?;
            let socket_client = SocketClient::new(&agent_socket_url, None, Some("/api/v1"))?;

            (rest_client, socket_client)
        } else {
            Self::create_remote_clients(Some(&base_url), api_key)?
        };

        let mut client = Self {
            agent_id: config.agent_id,
            entrypoint_tag: config.entrypoint_tag,
            local,
            rest_client,
            socket_client,
            serializer,
            agent_architecture: None,
            extra_params: config.extra_params,

            #[cfg(feature = "db")]
            db_service,
        };

        client.initialize_architecture().await?;

        Ok(client)
    }

    async fn initialize_architecture(&mut self) -> RunAgentResult<()> {
        let architecture = self.get_agent_architecture_internal().await?;
        self.agent_architecture = Some(architecture);
        self.validate_entrypoint()?;
        Ok(())
    }

    async fn get_agent_architecture_internal(&self) -> RunAgentResult<Value> {
        self.rest_client.get_agent_architecture(&self.agent_id).await
    }

    fn validate_entrypoint(&self) -> RunAgentResult<()> {
        if let Some(ref architecture) = self.agent_architecture {
            if let Some(entrypoints) = architecture.get("entrypoints").and_then(|e| e.as_array()) {
                let found = entrypoints.iter().any(|ep| {
                    ep.get("tag")
                        .and_then(|t| t.as_str())
                        .map(|t| t == self.entrypoint_tag)
                        .unwrap_or(false)
                });

                if !found {
                    let available: Vec<String> = entrypoints
                        .iter()
                        .filter_map(|ep| ep.get("tag").and_then(|t| t.as_str()))
                        .map(|s| s.to_string())
                        .collect();
                    tracing::error!(
                        "Entrypoint `{}` not found for agent {}. Available: {:?}",
                        self.entrypoint_tag,
                        self.agent_id,
                        available
                    );
                    return Err(RunAgentError::validation(format!(
                        "Entrypoint `{}` not found in agent {}",
                        self.entrypoint_tag, self.agent_id
                    )));
                }
            }
        }
        Ok(())
    }

    /// Run the agent with keyword arguments only
    pub async fn run(&self, input_kwargs: &[(&str, Value)]) -> RunAgentResult<Value> {
        self.run_with_args(&[], input_kwargs).await
    }

    /// Run the agent with the given input
    pub async fn run_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Value> {
        if self.entrypoint_tag.ends_with("_stream") {
            return Err(RunAgentError::validation(
                "Use run_stream for streaming entrypoints".to_string(),
            ));
        }

        let input_kwargs_map: HashMap<String, Value> = input_kwargs
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect();

        let response = self
            .rest_client
            .run_agent(
                &self.agent_id,
                &self.entrypoint_tag,
                input_args,
                &input_kwargs_map,
            )
            .await?;

        if response.get("success").and_then(|s| s.as_bool()).unwrap_or(false) {
            // Process response data
            let mut payload: Option<Value> = None;

            if let Some(data) = response.get("data") {
                // Case 1: data is a string (simplified payload - could be JSON string with {type, payload})
                if data.as_str().is_some() {
                    // Check for generator object BEFORE processing (case-insensitive)
                    if let Some(data_str) = data.as_str() {
                        let lower_str = data_str.to_lowercase();
                        if lower_str.contains("generator object") || lower_str.contains("<generator") {
                            let streaming_tag = format!("{}_stream", self.entrypoint_tag);
                            return Err(RunAgentError::validation(format!(
                                "Agent returned a generator object instead of content. This entrypoint appears to be a streaming function.\n\
                                Try using the streaming endpoint: `{}`\n\
                                Or use `run_stream()` method instead of `run()`.",
                                streaming_tag
                            )));
                        }
                    }
                    // Use common deserializer preparation logic
                    let prepared = self.serializer.prepare_for_deserialization(data.clone());
                    payload = Some(prepared);
                }
                // Case 2: data has result_data.data (legacy detailed execution payload)
                else if let Some(result_data) = data.get("result_data") {
                    if let Some(output_data) = result_data.get("data") {
                        // Check for generator object in nested data (case-insensitive)
                        if let Some(output_str) = output_data.as_str() {
                            let lower_str = output_str.to_lowercase();
                            if lower_str.contains("generator object") || lower_str.contains("<generator") {
                                let streaming_tag = format!("{}_stream", self.entrypoint_tag);
                                return Err(RunAgentError::validation(format!(
                                    "Agent returned a generator object instead of content. This entrypoint appears to be a streaming function.\n\
                                    Try using the streaming endpoint: `{}`\n\
                                    Or use `run_stream()` method instead of `run()`.",
                                    streaming_tag
                                )));
                            }
                        }
                        payload = Some(output_data.clone());
                    }
                }
                // Case 3: data is an object (could be {type, payload} structure)
                else if data.is_object() {
                    payload = Some(data.clone());
                }
            }
            // Case 4: Fallback to output_data (backward compatibility)
            else if let Some(output_data) = response.get("output_data") {
                // Check for generator object in output_data (case-insensitive)
                if let Some(output_str) = output_data.as_str() {
                    let lower_str = output_str.to_lowercase();
                    if lower_str.contains("generator object") || lower_str.contains("<generator") {
                        let streaming_tag = format!("{}_stream", self.entrypoint_tag);
                        return Err(RunAgentError::validation(format!(
                            "Agent returned a generator object instead of content. This entrypoint appears to be a streaming function.\n\
                            Try using the streaming endpoint: `{}`\n\
                            Or use `run_stream()` method instead of `run()`.",
                            streaming_tag
                        )));
                    }
                }
                payload = Some(output_data.clone());
            }

            // Deserialize the payload using serializer (handles {type, payload} structure)
            if let Some(payload_val) = payload {
                // Check for generator object warning (case-insensitive, after deserialization)
                if let Some(content_str) = payload_val.as_str() {
                    let lower_str = content_str.to_lowercase();
                    if lower_str.contains("generator object") || lower_str.contains("<generator") {
                        // Check if there's a streaming version of this entrypoint
                        let streaming_tag = format!("{}_stream", self.entrypoint_tag);
                        return Err(RunAgentError::validation(format!(
                            "Agent returned a generator object instead of content. This entrypoint appears to be a streaming function.\n\
                            Try using the streaming endpoint: `{}`\n\
                            Or use `run_stream()` method instead of `run()`.",
                            streaming_tag
                        )));
                    }
                }
                // Deserialize the payload - this should extract payload from {type, payload} structure
                let deserialized = self.serializer.deserialize_object(payload_val)?;
                return Ok(deserialized);
            }
            Ok(Value::Null)
        } else {
            // Handle new error format with ErrorDetail object (matching Python SDK)
            if let Some(error_info) = response.get("error") {
                if let Some(error_obj) = error_info.as_object() {
                    if let (Some(message), Some(code)) = (
                        error_obj.get("message").and_then(|m| m.as_str()),
                        error_obj.get("code").and_then(|c| c.as_str())
                    ) {
                        return Err(RunAgentError::server(format!("[{}] {}", code, message)));
                    }
                }
                // Fallback to old format
                if let Some(error_msg) = error_info.as_str() {
                    return Err(RunAgentError::server(error_msg));
                }
            }
            Err(RunAgentError::server("Unknown error"))
        }
    }

    /// Run the agent and return a stream of responses
    pub async fn run_stream(
        &self,
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        self.run_stream_with_args(&[], input_kwargs).await
    }

    /// Run the agent with streaming and both positional and keyword arguments
    pub async fn run_stream_with_args(
        &self,
        input_args: &[Value],
        input_kwargs: &[(&str, Value)],
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        if !self.entrypoint_tag.ends_with("_stream") {
            return Err(RunAgentError::validation(
                "Use run() for non-stream entrypoints".to_string(),
            ));
        }

        let input_kwargs_map: HashMap<String, Value> = input_kwargs
            .iter()
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect();

        self.socket_client
            .run_stream(&self.agent_id, &self.entrypoint_tag, input_args, &input_kwargs_map)
            .await
    }

    /// Get the agent's architecture information
    pub async fn get_agent_architecture(&self) -> RunAgentResult<Value> {
        self.rest_client.get_agent_architecture(&self.agent_id).await
    }

    /// Check if the agent is available
    pub async fn health_check(&self) -> RunAgentResult<bool> {
        match self.rest_client.health_check().await {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    /// Get agent information
    pub fn agent_id(&self) -> &str {
        &self.agent_id
    }

    /// Get entrypoint tag
    pub fn entrypoint_tag(&self) -> &str {
        &self.entrypoint_tag
    }

    /// Get any extra params supplied during initialization
    pub fn extra_params(&self) -> Option<&HashMap<String, Value>> {
        self.extra_params.as_ref()
    }

    /// Check if using local deployment
    pub fn is_local(&self) -> bool {
        self.local
    }
}

impl RunAgentClient {
    fn create_remote_clients(
        base_url_override: Option<&str>,
        api_key_override: Option<String>,
    ) -> RunAgentResult<(RestClient, SocketClient)> {
        if let Some(base_url) = base_url_override {
            let rest_client = RestClient::new(base_url, api_key_override.clone(), Some("/api/v1"))?;
            let socket_base = if base_url.starts_with("https://") {
                base_url.replace("https://", "wss://")
            } else if base_url.starts_with("http://") {
                base_url.replace("http://", "ws://")
            } else {
                format!("wss://{}", base_url)
            };
            let socket_client = SocketClient::new(&socket_base, api_key_override, Some("/api/v1"))?;
            Ok((rest_client, socket_client))
        } else {
            let rest_client = RestClient::default()?;
            let socket_client = SocketClient::default()?;
            Ok((rest_client, socket_client))
        }
    }
}