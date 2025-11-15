//! Constants for the RunAgent Client SDK
//!
//! Only client-related constants. No CLI features.

/// Environment variable for API key
pub const ENV_RUNAGENT_API_KEY: &str = "RUNAGENT_API_KEY";

/// Environment variable for base URL
pub const ENV_RUNAGENT_BASE_URL: &str = "RUNAGENT_BASE_URL";

/// Default base URL for remote agents
pub const DEFAULT_BASE_URL: &str = "https://backend.run-agent.ai";

/// Default API prefix
pub const DEFAULT_API_PREFIX: &str = "/api/v1";

/// Default timeout for agent execution (5 minutes)
pub const DEFAULT_TIMEOUT_SECONDS: u64 = 300;

/// Agent config file name (for reading agent configs, not for creating them)
pub const AGENT_CONFIG_FILE_NAME: &str = "runagent.config.json";

