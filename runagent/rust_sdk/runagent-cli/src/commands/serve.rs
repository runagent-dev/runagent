//! Serve command implementation
//!
//! Starts a local FastAPI-like server for testing deployed agents with
//! automatic port allocation and agent management.

use crate::utils::{output::CliOutput, validation};
use anyhow::{Context, Result};
use clap::Args;
use std::path::PathBuf;

#[cfg(feature = "server")]
use crate::server::LocalServer;

/// Start local FastAPI server for testing deployed agents
#[derive(Args)]
pub struct ServeArgs {
    /// Path to the agent directory
    #[arg(default_value = ".")]
    path: PathBuf,

    /// Preferred port (auto-allocated if unavailable)
    #[arg(short, long)]
    port: Option<u16>,

    /// Host to bind server to
    #[arg(long, default_value = "127.0.0.1")]
    host: String,

    /// Run server in debug mode
    #[arg(long)]
    debug: bool,

    /// Replace existing agent with this agent ID
    #[arg(long)]
    replace: Option<String>,

    /// Delete existing agent with this agent ID before serving
    #[arg(long)]
    delete: Option<String>,

    /// Force overwrite of existing agent without confirmation
    #[arg(long)]
    force: bool,
}

pub async fn execute(args: ServeArgs, output: &CliOutput) -> Result<()> {
    // Validate and resolve agent path
    let agent_path = args.path
        .canonicalize()
        .with_context(|| format!("Failed to resolve agent path: {}", args.path.display()))?;
    
    validation::validate_agent_directory(&agent_path)?;

    output.info("🚀 Starting local server...");
    output.info(&format!("📁 Agent path: {}", agent_path.display()));

    #[cfg(feature = "server")]
    {
        // Create and start the server
        let server = LocalServer::from_path(
            agent_path.clone(),
            Some(&args.host),
            args.port,
        ).await.context("Failed to create local server")?;

        let server_info = server.get_info();
        
        // Display server information
        output.success("✅ Local server ready!");
        output.info(&format!("🆔 Agent ID: {}", server_info.agent_id));
        output.info(&format!("🌐 URL: {}", server_info.url));
        output.info(&format!("📖 Docs: {}/docs", server_info.url));
        
        if args.debug {
            output.info("🔧 Debug mode enabled");
        }

        output.info("Press Ctrl+C to stop the server");
        output.separator();
        
        // Important: Print the agent ID clearly for easy copying
        println!("\n🆔 AGENT ID: {}", server_info.agent_id);
        println!("📋 Copy this ID to use with: runagent run --id {} --local", server_info.agent_id);
        println!("🔗 Or test with Rust SDK using this agent ID\n");

        // Start server (this will block until interrupted)
        server.start().await.context("Server failed to start")?;
    }

    #[cfg(not(feature = "server"))]
    {
        output.error("❌ Server feature is not enabled");
        output.info("💡 Rebuild with: cargo build --features server");
        return Err(anyhow::anyhow!("Server feature not enabled"));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    fn create_test_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();
        
        // Create a simple main.py file
        fs::write(agent_path.join("main.py"), "def run(): return 'Hello'").unwrap();
        fs::write(agent_path.join("requirements.txt"), "langchain").unwrap();
        
        // Create runagent config
        fs::write(
            agent_path.join("runagent.config.json"),
            r#"{"agent_name": "test", "framework": "langchain"}"#
        ).unwrap();
        
        temp_dir
    }

    #[tokio::test]
    async fn test_serve_args_parsing() {
        let args = ServeArgs {
            path: PathBuf::from("."),
            port: Some(8450),
            host: "localhost".to_string(),
            debug: false,
            replace: None,
            delete: None,
            force: false,
        };
        assert_eq!(args.port, Some(8450));
        assert_eq!(args.host, "localhost");
        assert!(!args.debug);
    }

    #[test]
    fn test_agent_validation() {
        let temp_dir = create_test_agent();
        let result = validation::validate_agent_directory(temp_dir.path());
        assert!(result.is_ok());
    }
}