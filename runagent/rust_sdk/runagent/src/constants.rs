//! Constants and configuration values for the RunAgent SDK

use once_cell::sync::Lazy;
use std::path::PathBuf;

/// Template repository URL
pub const TEMPLATE_REPO_URL: &str = "https://github.com/runagent-dev/runagent.git";

/// Template repository branch
pub const TEMPLATE_BRANCH: &str = "main";

/// Template pre-path
pub const TEMPLATE_PREPATH: &str = "templates";

/// Default framework
pub const DEFAULT_FRAMEWORK: &str = "langchain";

/// Default template
pub const DEFAULT_TEMPLATE: &str = "basic";

/// Environment variable for API key
pub const ENV_RUNAGENT_API_KEY: &str = "RUNAGENT_API_KEY";

/// Environment variable for base URL
pub const ENV_RUNAGENT_BASE_URL: &str = "RUNAGENT_BASE_URL";

/// Environment variable for cache directory
pub const ENV_LOCAL_CACHE_DIRECTORY: &str = "RUNAGENT_CACHE_DIR";

/// Environment variable for logging level
pub const ENV_RUNAGENT_LOGGING_LEVEL: &str = "RUNAGENT_LOGGING_LEVEL";

/// Default base URL
pub const DEFAULT_BASE_URL: &str = "http://52.237.88.147:8330/";

/// Agent config file name
pub const AGENT_CONFIG_FILE_NAME: &str = "runagent.config.json";

/// User data file name
pub const USER_DATA_FILE_NAME: &str = "user_data.json";

/// Default local cache directory path
const LOCAL_CACHE_DIRECTORY_PATH: &str = "~/.runagent";

/// Default port range for local servers
pub const DEFAULT_PORT_START: u16 = 8450;
pub const DEFAULT_PORT_END: u16 = 8500;

/// Database file name
pub const DATABASE_FILE_NAME: &str = "runagent_local.db";

/// Maximum number of local agents
pub const MAX_LOCAL_AGENTS: usize = 5;

/// Local cache directory (computed at runtime)
pub static LOCAL_CACHE_DIRECTORY: Lazy<PathBuf> = Lazy::new(|| {
    std::env::var(ENV_LOCAL_CACHE_DIRECTORY)
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            directories::ProjectDirs::from("com", "runagent", "runagent")
                .map(|proj_dirs| proj_dirs.config_dir().to_path_buf())
                .unwrap_or_else(|| {
                    // Fallback to home directory
                    dirs::home_dir()
                        .unwrap_or_else(|| PathBuf::from("."))
                        .join(".runagent")
                })
        })
});

/// Supported frameworks
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Framework {
    LangGraph,
    LangChain,
    LlamaIndex,
    CrewAI,
    AutoGen,
    Default,
}

impl Framework {
    pub fn as_str(&self) -> &'static str {
        match self {
            Framework::LangGraph => "langgraph",
            Framework::LangChain => "langchain",
            Framework::LlamaIndex => "llamaindex",
            Framework::CrewAI => "crewai",
            Framework::AutoGen => "autogen",
            Framework::Default => "default",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "langgraph" => Some(Framework::LangGraph),
            "langchain" => Some(Framework::LangChain),
            "llamaindex" => Some(Framework::LlamaIndex),
            "crewai" => Some(Framework::CrewAI),
            "autogen" => Some(Framework::AutoGen),
            "default" => Some(Framework::Default),
            _ => None,
        }
    }
}

/// Template variants
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TemplateVariant {
    Basic,
    Advanced,
}

impl TemplateVariant {
    pub fn as_str(&self) -> &'static str {
        match self {
            TemplateVariant::Basic => "basic",
            TemplateVariant::Advanced => "advanced",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "basic" => Some(TemplateVariant::Basic),
            "advanced" => Some(TemplateVariant::Advanced),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_framework_conversion() {
        assert_eq!(Framework::LangChain.as_str(), "langchain");
        assert_eq!(Framework::from_str("langchain"), Some(Framework::LangChain));
        assert_eq!(Framework::from_str("invalid"), None);
    }

    #[test]
    fn test_template_variant_conversion() {
        assert_eq!(TemplateVariant::Basic.as_str(), "basic");
        assert_eq!(TemplateVariant::from_str("basic"), Some(TemplateVariant::Basic));
        assert_eq!(TemplateVariant::from_str("invalid"), None);
    }

    #[test]
    fn test_cache_directory() {
        let dir = &*LOCAL_CACHE_DIRECTORY;
        assert!(dir.to_str().is_some());
    }
}