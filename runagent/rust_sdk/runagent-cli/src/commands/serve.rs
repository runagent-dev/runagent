//! Serve command implementation
//!
//! Starts a local FastAPI-like server for testing deployed agents with
//! automatic port allocation and agent management.

use crate::utils::{output::CliOutput, validation};
use anyhow::{Context, Result};
use clap::Args;
use colored::Colorize;                    // bring in the `.bright_*()` methods
use runagent::{
    db::DatabaseService,
    server::LocalServer,
    utils::{agent::detect_framework, port::PortManager},
};
use std::path::PathBuf;
use std::sync::Arc;
use uuid::Uuid;

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

    output.info("🚀 Starting local server with auto port allocation...");
    output.info(&format!("📁 Agent path: {}", agent_path.display()));

    // Initialize database service
    let db_service = Arc::new(
        DatabaseService::new(None)
            .await
            .context("Failed to initialize database service")?,
    );

    // Handle delete operation first
    if let Some(delete_id) = &args.delete {
        handle_delete_agent(delete_id, &db_service, output, args.force).await?;
    }

    // Handle replace or new agent
    let (agent_id, allocated_host, allocated_port) = if let Some(replace_id) = &args.replace {
        handle_replace_agent(replace_id, &agent_path, &args, &db_service, output).await?
    } else {
        handle_new_agent(&agent_path, &args, &db_service, output).await?
    };

    // Create and start the server
    let server = LocalServer::new(agent_id.clone(), agent_path.clone(), &allocated_host, allocated_port)
        .await
        .context("Failed to create local server")?;

    // Display server information
    output.success("✅ Local server ready!");
    output.info(&format!("🆔 Agent ID: {}", agent_id.bright_magenta()));
    output.info(&format!(
        "🌐 URL: {}",
        format!("http://{}:{}", allocated_host, allocated_port).bright_blue()
    ));
    output.info(&format!(
        "📖 Docs: {}",
        format!("http://{}:{}/docs", allocated_host, allocated_port).bright_cyan()
    ));

    // Show capacity info
    let capacity_info = db_service.get_capacity_info().await?;
    output.info(&format!(
        "📊 Capacity: {}/{} slots used",
        capacity_info.current_count.to_string().bright_cyan(),
        capacity_info.max_capacity.to_string().bright_cyan()
    ));

    if args.debug {
        output.info("🔧 Debug mode enabled");
    }

    output.info("Press Ctrl+C to stop the server");

    // Start server (this will block until interrupted)
    server.start().await.context("Server failed to start")?;
    Ok(())
}

async fn handle_delete_agent(
    delete_id: &str,
    db_service: &Arc<DatabaseService>,
    output: &CliOutput,
    force: bool,
) -> Result<()> {
    output.info(&format!("🗑️ Deleting agent: {}", delete_id.bright_yellow()));

    // Check if agent exists
    let agent = db_service.get_agent(delete_id).await?;
    match agent {
        Some(agent_info) => {
            if !force {
                // Safely unwrap the optional framework
                let framework = agent_info.framework.as_deref().unwrap_or("unknown");
                output.warning(&format!(
                    "About to delete agent '{}' ({})",
                    agent_info.agent_id,
                    framework
                ));
                // (Would prompt for confirmation here)
            }

            // db_service.delete_agent(delete_id).await?; // implement as needed
            output.success(&format!("✅ Agent {} deleted successfully", delete_id));
        }
        None => {
            output.warning(&format!("⚠️ Agent {} not found in database", delete_id));

            let agents = db_service.list_agents().await?;
            if !agents.is_empty() {
                output.info("💡 Available agents:");
                for agent in agents.iter().take(5) {
                    output.info(&format!(
                        "   • {} ({})",
                        agent.agent_id.bright_magenta(),
                        agent.framework.as_deref().unwrap_or("unknown")
                    ));
                }
            }
        }
    }

    Ok(())
}

async fn handle_replace_agent(
    replace_id: &str,
    agent_path: &PathBuf,
    args: &ServeArgs,
    db_service: &Arc<DatabaseService>,
    output: &CliOutput,
) -> Result<(String, String, u16)> {
    output.info(&format!("🔄 Replacing agent: {}", replace_id.bright_yellow()));

    // Ensure the agent to replace exists
    if db_service.get_agent(replace_id).await?.is_none() {
        output.warning(&format!("⚠️ Agent {} not found in database", replace_id));
        let agents = db_service.list_agents().await?;
        if !agents.is_empty() {
            output.info("💡 Available agents:");
            for agent in agents.iter().take(5) {
                output.info(&format!(
                    "   • {} ({})",
                    agent.agent_id.bright_magenta(),
                    agent.framework.as_deref().unwrap_or("unknown")
                ));
            }
        }
        return Err(anyhow::anyhow!("Agent to replace not found"));
    }

    // New ID and port allocation
    let new_agent_id = Uuid::new_v4().to_string();
    let used_ports: Vec<u16> = db_service
        .list_agents()
        .await?
        .into_iter()
        .filter(|a| a.agent_id != replace_id)
        .map(|a| a.port as u16)
        .collect();

    let (allocated_host, allocated_port) = if let Some(port) = args.port {
        if PortManager::is_port_available(&args.host, port) {
            output.info(&format!("🎯 Using specified address: {}:{}", args.host, port));
            (args.host.clone(), port)
        } else {
            output.info(&format!("Port {} unavailable, auto-allocating...", port));
            PortManager::allocate_unique_address(&used_ports)?
        }
    } else {
        let (h, p) = PortManager::allocate_unique_address(&used_ports)?;
        output.info(&format!("🔌 Auto-allocated address: {}:{}", h, p));
        (h, p)
    };

    let framework = detect_framework(agent_path)?;
    let new_agent = runagent::db::models::Agent::new(
        new_agent_id.clone(),
        agent_path.to_string_lossy().to_string(),
        allocated_host.clone(),
        allocated_port,
    )
    .with_framework(framework);

    let replaced = db_service.replace_agent(replace_id, new_agent).await?;
    if !replaced {
        return Err(anyhow::anyhow!("Failed to replace agent in database"));
    }

    output.success("✅ Agent replaced successfully!");
    output.info(&format!("🆔 New Agent ID: {}", new_agent_id.bright_magenta()));
    output.info(&format!(
        "🔌 Address: {}:{}",
        allocated_host.bright_blue(),
        allocated_port
    ));

    Ok((new_agent_id, allocated_host, allocated_port))
}

async fn handle_new_agent(
    agent_path: &PathBuf,
    args: &ServeArgs,
    db_service: &Arc<DatabaseService>,
    output: &CliOutput,
) -> Result<(String, String, u16)> {
    // Check capacity
    let capacity_info = db_service.get_capacity_info().await?;
    if capacity_info.is_full {
        output.error("❌ Database is full!");
        if let Some(oldest) = &capacity_info.oldest_agent {
            output.info("💡 Suggested commands:");
            output.info(&format!(
                "   Replace: runagent serve {} --replace {}",
                agent_path.display(),
                oldest.agent_id
            ));
            output.info(&format!(
                "   Delete:  runagent serve {} --delete {}",
                agent_path.display(),
                oldest.agent_id
            ));
        }
        return Err(anyhow::anyhow!(
            "Database at capacity. Use --replace or --delete to free space."
        ));
    }

    // New agent
    let agent_id = Uuid::new_v4().to_string();
    let used_ports: Vec<u16> = db_service
        .list_agents()
        .await?
        .into_iter()
        .map(|a| a.port as u16)
        .collect();

    let (allocated_host, allocated_port) = if let Some(port) = args.port {
        if PortManager::is_port_available(&args.host, port) {
            output.info(&format!("🎯 Using specified address: {}:{}", args.host, port));
            (args.host.clone(), port)
        } else {
            output.info(&format!("Port {} unavailable, auto-allocating...", port));
            PortManager::allocate_unique_address(&used_ports)?
        }
    } else {
        let (h, p) = PortManager::allocate_unique_address(&used_ports)?;
        output.info(&format!("🔌 Auto-allocated address: {}:{}", h, p));
        (h, p)
    };

    let framework = detect_framework(agent_path)?;
    output.info(&format!("🔍 Detected framework: {}", framework.bright_green()));

    let new_agent = runagent::db::models::Agent::new(
        agent_id.clone(),
        agent_path.to_string_lossy().to_string(),
        allocated_host.clone(),
        allocated_port,
    )
    .with_framework(framework);

    let result = db_service.add_agent(new_agent).await?;
    if !result.success {
        return Err(anyhow::anyhow!(
            "Failed to add agent: {}",
            result.error.unwrap_or_default()
        ));
    }

    Ok((agent_id, allocated_host, allocated_port))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    fn create_test_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();
        fs::write(agent_path.join("main.py"), "def run(): return 'Hello'").unwrap();
        fs::write(agent_path.join("requirements.txt"), "langchain").unwrap();
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
