//! Framework-specific executors for different AI agent frameworks
//!
//! This module provides execution environments for various AI agent frameworks
//! including LangChain, LangGraph, LlamaIndex, and generic Python frameworks.

pub mod generic;
pub mod langchain;
pub mod langgraph;

// Re-export the main types and functions
pub use generic::GenericExecutor;
pub use langchain::LangChainExecutor;
pub use langgraph::LangGraphExecutor;

use crate::types::{RunAgentError, RunAgentResult, EntryPoint};
use crate::utils::imports::ImportResolver;
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;
use std::pin::Pin;

/// Trait for framework-specific executors
pub trait FrameworkExecutor {
    /// Execute a non-streaming entrypoint
    fn execute(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value>;

    /// Execute a streaming entrypoint
    fn execute_stream(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>>;

    /// Get available entrypoints for this framework
    fn get_entrypoints(&self) -> Vec<String>;

    /// Get framework name
    fn framework_name(&self) -> &'static str;

    /// Check if an entrypoint is supported
    fn supports_entrypoint(&self, entrypoint: &EntryPoint) -> bool {
        self.get_entrypoints().contains(&entrypoint.tag)
    }
}

/// Factory function to create appropriate executor based on framework
pub fn create_executor<P: AsRef<Path>>(
    framework: &str,
    agent_dir: P,
) -> RunAgentResult<Box<dyn FrameworkExecutor + Send + Sync>> {
    match framework.to_lowercase().as_str() {
        "langchain" => Ok(Box::new(LangChainExecutor::new(agent_dir)?)),
        "langgraph" => Ok(Box::new(LangGraphExecutor::new(agent_dir)?)),
        "llamaindex" => {
            // For now, use generic executor for LlamaIndex
            // Could be extended with specific LlamaIndex logic
            Ok(Box::new(GenericExecutor::new(agent_dir)?))
        }
        "letta" => {
            // Letta uses generic execution patterns
            Ok(Box::new(GenericExecutor::new(agent_dir)?))
        }
        "crewai" => {
            // CrewAI uses generic execution patterns
            Ok(Box::new(GenericExecutor::new(agent_dir)?))
        }
        "autogen" => {
            // AutoGen uses generic execution patterns
            Ok(Box::new(GenericExecutor::new(agent_dir)?))
        }
        "generic" | "default" | _ => Ok(Box::new(GenericExecutor::new(agent_dir)?)),
    }
}

/// Get supported frameworks
pub fn supported_frameworks() -> Vec<&'static str> {
    vec![
        "generic",
        "default", 
        "langchain",
        "langgraph",
        "llamaindex",
        "letta",
        "crewai",
        "autogen",
    ]
}

/// Check if a framework is supported
pub fn is_framework_supported(framework: &str) -> bool {
    supported_frameworks().contains(&framework.to_lowercase().as_str())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_create_executor_generic() {
        let temp_dir = TempDir::new().unwrap();
        let executor = create_executor("generic", temp_dir.path());
        assert!(executor.is_ok());
        assert_eq!(executor.unwrap().framework_name(), "generic");
    }

    #[test]
    fn test_create_executor_langchain() {
        let temp_dir = TempDir::new().unwrap();
        let executor = create_executor("langchain", temp_dir.path());
        assert!(executor.is_ok());
        assert_eq!(executor.unwrap().framework_name(), "langchain");
    }

    #[test]
    fn test_create_executor_langgraph() {
        let temp_dir = TempDir::new().unwrap();
        let executor = create_executor("langgraph", temp_dir.path());
        assert!(executor.is_ok());
        assert_eq!(executor.unwrap().framework_name(), "langgraph");
    }

    #[test]
    fn test_supported_frameworks() {
        let frameworks = supported_frameworks();
        assert!(frameworks.contains(&"generic"));
        assert!(frameworks.contains(&"langchain"));
        assert!(frameworks.contains(&"langgraph"));
        assert!(frameworks.contains(&"letta"));
    }

    #[test]
    fn test_is_framework_supported() {
        assert!(is_framework_supported("langchain"));
        assert!(is_framework_supported("LangChain")); // Case insensitive
        assert!(is_framework_supported("generic"));
        assert!(!is_framework_supported("unknown_framework"));
    }
}