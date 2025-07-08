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