//! Validation utilities for CLI commands

use anyhow::{Context, Result};
use std::fs;
use std::path::Path;

/// Validate that a directory exists and is suitable for an agent
pub fn validate_agent_directory<P: AsRef<Path>>(path: P) -> Result<()> {
    let path = path.as_ref();
    
    if !path.exists() {
        return Err(anyhow::anyhow!("Directory does not exist: {}", path.display()));
    }
    
    if !path.is_dir() {
        return Err(anyhow::anyhow!("Path is not a directory: {}", path.display()));
    }
    
    // Check if directory has some agent-like files
    let has_python = has_python_files(path)?;
    let has_rust = has_rust_files(path)?;
    let has_config = has_config_files(path)?;
    
    if !has_python && !has_rust && !has_config {
        return Err(anyhow::anyhow!(
            "Directory does not appear to contain an agent project. Expected Python files (.py), Rust files (Cargo.toml), or config files."
        ));
    }
    
    Ok(())
}

/// Check if directory contains Python files
pub fn has_python_files<P: AsRef<Path>>(path: P) -> Result<bool> {
    let path = path.as_ref();
    
    // Check for common Python files
    let python_files = ["main.py", "agent.py", "run.py", "app.py", "__init__.py"];
    for file in &python_files {
        if path.join(file).exists() {
            return Ok(true);
        }
    }
    
    // Check for requirements.txt
    if path.join("requirements.txt").exists() {
        return Ok(true);
    }
    
    // Check for any .py files
    let entries = fs::read_dir(path)
        .with_context(|| format!("Failed to read directory: {}", path.display()))?;
    
    for entry in entries {
        let entry = entry?;
        let file_name = entry.file_name();
        if let Some(name) = file_name.to_str() {
            if name.ends_with(".py") {
                return Ok(true);
            }
        }
    }
    
    Ok(false)
}

/// Check if directory contains Rust files
pub fn has_rust_files<P: AsRef<Path>>(path: P) -> Result<bool> {
    let path = path.as_ref();
    
    // Check for Cargo.toml
    if path.join("Cargo.toml").exists() {
        return Ok(true);
    }
    
    // Check for src directory with Rust files
    let src_dir = path.join("src");
    if src_dir.exists() && src_dir.is_dir() {
        let entries = fs::read_dir(&src_dir)
            .with_context(|| format!("Failed to read src directory: {}", src_dir.display()))?;
        
        for entry in entries {
            let entry = entry?;
            let file_name = entry.file_name();
            if let Some(name) = file_name.to_str() {
                if name.ends_with(".rs") {
                    return Ok(true);
                }
            }
        }
    }
    
    Ok(false)
}

/// Check if directory contains configuration files
pub fn has_config_files<P: AsRef<Path>>(path: P) -> Result<bool> {
    let path = path.as_ref();
    
    let config_files = [
        "runagent.config.json",
        "agent.yaml", 
        "agent.yml",
        "config.json",
        "config.yaml",
        "config.yml",
        ".env"
    ];
    
    for file in &config_files {
        if path.join(file).exists() {
            return Ok(true);
        }
    }
    
    Ok(false)
}

/// Validate project name for initialization
pub fn validate_project_name(name: &str) -> Result<()> {
    if name.is_empty() {
        return Err(anyhow::anyhow!("Project name cannot be empty"));
    }
    
    if name.len() > 50 {
        return Err(anyhow::anyhow!("Project name too long (max 50 characters)"));
    }
    
    // Check for valid characters
    let valid_chars = name.chars().all(|c| {
        c.is_alphanumeric() || c == '-' || c == '_' || c == '.'
    });
    
    if !valid_chars {
        return Err(anyhow::anyhow!(
            "Project name can only contain letters, numbers, hyphens, underscores, and dots"
        ));
    }
    
    // Check that it doesn't start with special characters
    if name.starts_with('-') || name.starts_with('.') {
        return Err(anyhow::anyhow!(
            "Project name cannot start with '-' or '.'"
        ));
    }
    
    Ok(())
}

/// Validate port number
pub fn validate_port(port: u16) -> Result<()> {
    if port < 1024 {
        return Err(anyhow::anyhow!(
            "Port number should be >= 1024 (current: {})", port
        ));
    }
    
    if port > 65535 {
        return Err(anyhow::anyhow!(
            "Port number should be <= 65535 (current: {})", port
        ));
    }
    
    Ok(())
}

/// Validate host address
pub fn validate_host(host: &str) -> Result<()> {
    if host.is_empty() {
        return Err(anyhow::anyhow!("Host cannot be empty"));
    }
    
    // Basic validation - could be more comprehensive
    if host == "localhost" || host == "127.0.0.1" || host == "0.0.0.0" {
        return Ok(());
    }
    
    // Basic IP address pattern check
    if host.parse::<std::net::IpAddr>().is_ok() {
        return Ok(());
    }
    
    // Basic hostname pattern check
    if host.chars().all(|c| c.is_alphanumeric() || c == '.' || c == '-') {
        return Ok(());
    }
    
    Err(anyhow::anyhow!("Invalid host address: {}", host))
}

/// Validate API key format
pub fn validate_api_key(api_key: &str) -> Result<()> {
    if api_key.is_empty() {
        return Err(anyhow::anyhow!("API key cannot be empty"));
    }
    
    if api_key.len() < 10 {
        return Err(anyhow::anyhow!("API key too short (minimum 10 characters)"));
    }
    
    if api_key.len() > 200 {
        return Err(anyhow::anyhow!("API key too long (maximum 200 characters)"));
    }
    
    Ok(())
}

/// Validate URL format
pub fn validate_url(url: &str) -> Result<()> {
    if url.is_empty() {
        return Err(anyhow::anyhow!("URL cannot be empty"));
    }
    
    // Try to parse as URL
    let parsed = url::Url::parse(url)
        .with_context(|| format!("Invalid URL format: {}", url))?;
    
    // Check scheme
    match parsed.scheme() {
        "http" | "https" => Ok(()),
        _ => Err(anyhow::anyhow!("URL must use http or https scheme: {}", url)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_python_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let path = temp_dir.path();
        
        fs::write(path.join("main.py"), "def run(): pass").unwrap();
        fs::write(path.join("requirements.txt"), "langchain").unwrap();
        
        temp_dir
    }

    fn create_test_rust_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let path = temp_dir.path();
        
        fs::write(path.join("Cargo.toml"), "[package]\nname = \"agent\"").unwrap();
        fs::create_dir(path.join("src")).unwrap();
        fs::write(path.join("src/main.rs"), "fn main() {}").unwrap();
        
        temp_dir
    }

    #[test]
    fn test_validate_python_agent_directory() {
        let temp_dir = create_test_python_agent();
        let result = validate_agent_directory(temp_dir.path());
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_rust_agent_directory() {
        let temp_dir = create_test_rust_agent();
        let result = validate_agent_directory(temp_dir.path());
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_empty_directory() {
        let temp_dir = TempDir::new().unwrap();
        let result = validate_agent_directory(temp_dir.path());
        assert!(result.is_err());
    }

    #[test]
    fn test_has_python_files() {
        let temp_dir = create_test_python_agent();
        let result = has_python_files(temp_dir.path()).unwrap();
        assert!(result);
    }

    #[test]
    fn test_has_rust_files() {
        let temp_dir = create_test_rust_agent();
        let result = has_rust_files(temp_dir.path()).unwrap();
        assert!(result);
    }

    #[test]
    fn test_validate_project_name() {
        assert!(validate_project_name("my-agent").is_ok());
        assert!(validate_project_name("my_agent").is_ok());
        assert!(validate_project_name("agent123").is_ok());
        
        assert!(validate_project_name("").is_err());
        assert!(validate_project_name("-invalid").is_err());
        assert!(validate_project_name(".invalid").is_err());
        assert!(validate_project_name("invalid@name").is_err());
    }

    #[test]
    fn test_validate_port() {
        assert!(validate_port(8080).is_ok());
        assert!(validate_port(3000).is_ok());
        assert!(validate_port(65535).is_ok());
        
        assert!(validate_port(80).is_err()); // < 1024
        assert!(validate_port(0).is_err());
    }

    #[test]
    fn test_validate_host() {
        assert!(validate_host("localhost").is_ok());
        assert!(validate_host("127.0.0.1").is_ok());
        assert!(validate_host("192.168.1.1").is_ok());
        assert!(validate_host("example.com").is_ok());
        
        assert!(validate_host("").is_err());
    }

    #[test]
    fn test_validate_api_key() {
        assert!(validate_api_key("valid-api-key-123").is_ok());
        assert!(validate_api_key("sk-1234567890abcdef").is_ok());
        
        assert!(validate_api_key("").is_err());
        assert!(validate_api_key("short").is_err());
        assert!(validate_api_key(&"x".repeat(201)).is_err());
    }

    #[test]
    fn test_validate_url() {
        assert!(validate_url("https://api.example.com").is_ok());
        assert!(validate_url("http://localhost:8000").is_ok());
        
        assert!(validate_url("").is_err());
        assert!(validate_url("ftp://example.com").is_err());
        assert!(validate_url("invalid-url").is_err());
    }
}