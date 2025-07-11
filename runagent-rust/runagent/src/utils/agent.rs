//! Agent utilities for framework detection and validation

use crate::constants::AGENT_CONFIG_FILE_NAME;
use crate::types::{RunAgentError, RunAgentResult, RunAgentConfig};
use std::fs;
use std::path::Path;

/// Detect the framework used by an agent
pub fn detect_framework<P: AsRef<Path>>(agent_path: P) -> RunAgentResult<String> {
    let agent_path = agent_path.as_ref();
    
    // Try to read the agent config file
    let config_path = agent_path.join(AGENT_CONFIG_FILE_NAME);
    
    if config_path.exists() {
        let config_content = fs::read_to_string(&config_path)
            .map_err(|e| RunAgentError::validation(format!("Failed to read config file: {}", e)))?;
        
        let config: RunAgentConfig = serde_json::from_str(&config_content)
            .map_err(|e| RunAgentError::validation(format!("Failed to parse config file: {}", e)))?;
        
        return Ok(config.framework);
    }
    
    // Fallback: try to detect from file contents
    detect_framework_from_files(agent_path)
}

/// Detect framework from analyzing Python files
fn detect_framework_from_files<P: AsRef<Path>>(agent_path: P) -> RunAgentResult<String> {
    let agent_path = agent_path.as_ref();
    
    let framework_keywords = [
        ("langgraph", vec!["langgraph", "StateGraph", "Graph"]),
        ("langchain", vec!["langchain", "ConversationChain", "AgentExecutor"]),
        ("llamaindex", vec!["llama_index", "VectorStoreIndex", "QueryEngine"]),
        ("letta", vec!["letta", "MemGPT"]),
    ];
    
    // Check main Python files
    for file_name in ["main.py", "agent.py", "run.py"] {
        let file_path = agent_path.join(file_name);
        if file_path.exists() {
            if let Ok(content) = fs::read_to_string(&file_path) {
                let content_lower = content.to_lowercase();
                
                for (framework, keywords) in &framework_keywords {
                    if keywords.iter().any(|keyword| content_lower.contains(&keyword.to_lowercase())) {
                        return Ok(framework.to_string());
                    }
                }
            }
        }
    }
    
    // Check requirements.txt
    let req_file = agent_path.join("requirements.txt");
    if req_file.exists() {
        if let Ok(content) = fs::read_to_string(&req_file) {
            let content_lower = content.to_lowercase();
            
            for (framework, keywords) in &framework_keywords {
                if keywords.iter().any(|keyword| content_lower.contains(&keyword.to_lowercase())) {
                    return Ok(framework.to_string());
                }
            }
        }
    }
    
    Ok("unknown".to_string())
}

/// Validate an agent project structure
pub fn validate_agent<P: AsRef<Path>>(agent_path: P) -> RunAgentResult<ValidationResult> {
    let agent_path = agent_path.as_ref();
    
    let mut result = ValidationResult {
        valid: false,
        errors: Vec::new(),
        warnings: Vec::new(),
        files_found: Vec::new(),
        missing_files: Vec::new(),
    };
    
    // Check if directory exists
    if !agent_path.exists() {
        result.errors.push(format!("Agent directory not found: {}", agent_path.display()));
        return Ok(result);
    }
    
    if !agent_path.is_dir() {
        result.errors.push(format!("Agent path is not a directory: {}", agent_path.display()));
        return Ok(result);
    }
    
    // Check for required files
    let required_files = [AGENT_CONFIG_FILE_NAME];
    
    for file_name in &required_files {
        let file_path = agent_path.join(file_name);
        if file_path.exists() {
            result.files_found.push(file_name.to_string());
        } else {
            result.missing_files.push(file_name.to_string());
            result.errors.push(format!("Required file missing: {}", file_name));
        }
    }
    
    // Check for suggested files
    let suggested_files = ["requirements.txt", "main.py", "agent.py"];
    
    for file_name in &suggested_files {
        let file_path = agent_path.join(file_name);
        if file_path.exists() {
            result.files_found.push(file_name.to_string());
        } else {
            result.warnings.push(format!("Suggested file missing: {}", file_name));
        }
    }
    
    // Validate config file if it exists
    if result.files_found.contains(&AGENT_CONFIG_FILE_NAME.to_string()) {
        if let Err(e) = validate_config_file(agent_path) {
            result.errors.push(format!("Config file validation failed: {}", e));
        }
    }
    
    // Check for unwanted files
    let unwanted_files = [".env"];
    
    for file_name in &unwanted_files {
        let file_path = agent_path.join(file_name);
        if file_path.exists() {
            result.warnings.push(format!("Unwanted file found: {} (should not be committed)", file_name));
        }
    }
    
    // Determine if validation passed
    result.valid = result.errors.is_empty();
    
    Ok(result)
}

/// Validate the agent config file
fn validate_config_file<P: AsRef<Path>>(agent_path: P) -> RunAgentResult<()> {
    let config_path = agent_path.as_ref().join(AGENT_CONFIG_FILE_NAME);
    
    let config_content = fs::read_to_string(&config_path)
        .map_err(|e| RunAgentError::validation(format!("Failed to read config file: {}", e)))?;
    
    let _config: RunAgentConfig = serde_json::from_str(&config_content)
        .map_err(|e| RunAgentError::validation(format!("Invalid config file format: {}", e)))?;
    
    // Additional validation could be added here
    
    Ok(())
}

/// Get agent configuration from config file
pub fn get_agent_config<P: AsRef<Path>>(agent_path: P) -> RunAgentResult<RunAgentConfig> {
    let config_path = agent_path.as_ref().join(AGENT_CONFIG_FILE_NAME);
    
    let config_content = fs::read_to_string(&config_path)
        .map_err(|e| RunAgentError::validation(format!("Failed to read config file: {}", e)))?;
    
    let config: RunAgentConfig = serde_json::from_str(&config_content)
        .map_err(|e| RunAgentError::validation(format!("Failed to parse config file: {}", e)))?;
    
    Ok(config)
}

/// Result of agent validation
#[derive(Debug, Clone)]
pub struct ValidationResult {
    /// Whether the agent passed validation
    pub valid: bool,
    /// List of validation errors
    pub errors: Vec<String>,
    /// List of validation warnings
    pub warnings: Vec<String>,
    /// List of files that were found
    pub files_found: Vec<String>,
    /// List of required files that are missing
    pub missing_files: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::TempDir;

    fn create_test_agent_config() -> serde_json::Value {
        json!({
            "agent_name": "test-agent",
            "description": "A test agent",
            "framework": "langchain",
            "template": "basic",
            "version": "1.0.0",
            "created_at": "2023-01-01T00:00:00Z",
            "template_source": {
                "repo_url": "https://github.com/test/test.git",
                "author": "test",
                "path": "test"
            },
            "agent_architecture": {
                "entrypoints": [
                    {
                        "file": "main.py",
                        "module": "run",
                        "tag": "generic"
                    }
                ]
            },
            "env_vars": {}
        })
    }

    #[test]
    fn test_detect_framework_from_config() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create config file
        let config = create_test_agent_config();
        let config_path = agent_path.join(AGENT_CONFIG_FILE_NAME);
        fs::write(&config_path, config.to_string()).unwrap();

        let framework = detect_framework(agent_path).unwrap();
        assert_eq!(framework, "langchain");
    }

    #[test]
    fn test_detect_framework_from_files() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create a Python file with LangChain imports
        let main_py = agent_path.join("main.py");
        fs::write(&main_py, "from langchain.chains import ConversationChain").unwrap();

        let framework = detect_framework(agent_path).unwrap();
        assert_eq!(framework, "langchain");
    }

    #[test]
    fn test_validate_agent_valid() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create required files
        let config = create_test_agent_config();
        let config_path = agent_path.join(AGENT_CONFIG_FILE_NAME);
        fs::write(&config_path, config.to_string()).unwrap();

        let result = validate_agent(agent_path).unwrap();
        assert!(result.valid);
        assert!(result.errors.is_empty());
    }

    #[test]
    fn test_validate_agent_missing_config() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        let result = validate_agent(agent_path).unwrap();
        assert!(!result.valid);
        assert!(!result.errors.is_empty());
        assert!(result.missing_files.contains(&AGENT_CONFIG_FILE_NAME.to_string()));
    }

    #[test]
    fn test_get_agent_config() {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create config file
        let config = create_test_agent_config();
        let config_path = agent_path.join(AGENT_CONFIG_FILE_NAME);
        fs::write(&config_path, config.to_string()).unwrap();

        let result = get_agent_config(agent_path);
        assert!(result.is_ok());
        
        let config = result.unwrap();
        assert_eq!(config.agent_name, "test-agent");
        assert_eq!(config.framework, "langchain");
    }
}