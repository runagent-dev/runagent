//! RunAgent CLI - Deploy and manage AI agents easily
//!
//! This is the main entry point for the RunAgent CLI, providing the same
//! interface as the Python CLI but implemented in Rust for better performance.

use clap::{Parser, Subcommand};
use colored::Colorize;
use std::process;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

mod commands;
mod config;
mod utils;

use commands::*;
use utils::output::CliOutput;

/// RunAgent CLI - Deploy and manage AI agents easily
#[derive(Parser)]
#[command(name = "runagent")]
#[command(about = "RunAgent CLI - Deploy and manage AI agents easily")]
#[command(version = env!("CARGO_PKG_VERSION"))]
#[command(long_about = "
RunAgent CLI provides a unified interface for deploying and managing AI agents
across different frameworks like LangChain, LangGraph, LlamaIndex, and custom Rust agents.

Examples:
  runagent serve ./my-agent --port 8450
  runagent init my-new-agent --framework langchain --interactive  
  runagent deploy-local --folder ./agent
  runagent run --id agent-123 --message='Hello World'
")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Enable verbose output
    #[arg(short, long, global = true)]
    verbose: bool,

    /// Disable colored output
    #[arg(long, global = true)]
    no_color: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Setup RunAgent authentication
    Setup(SetupArgs),

    /// Remove RunAgent configuration  
    Teardown(TeardownArgs),

    /// Initialize a new RunAgent project
    Init(InitArgs),

    /// Manage project templates
    Template(TemplateArgs),

    /// Deploy agent locally for testing
    #[command(name = "deploy-local")]
    DeployLocal(DeployLocalArgs),

    /// Upload agent to remote server
    Upload(UploadArgs),

    /// Start an uploaded agent on remote server
    Start(StartArgs),

    /// Deploy agent (upload + start) or deploy locally
    Deploy(DeployArgs),

    /// Start local FastAPI server for testing deployed agents
    Serve(ServeArgs),

    /// Run an agent with flexible configuration options
    Run(RunArgs),

    /// Show local database status and statistics
    #[command(name = "db-status")]
    DbStatus(DbStatusArgs),
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    // Initialize logging
    init_logging(cli.verbose);

    // Set up colored output
    if cli.no_color {
        colored::control::set_override(false);
    }

    let output = CliOutput::new(!cli.no_color);

    // Execute command
    let result = match cli.command {
        Commands::Setup(args) => setup::execute(args, &output).await,
        Commands::Teardown(args) => teardown::execute(args, &output).await,
        Commands::Init(args) => init::execute(args, &output).await,
        Commands::Template(args) => template::execute(args, &output).await,
        Commands::DeployLocal(args) => deploy::execute_deploy_local(args, &output).await,
        Commands::Upload(args) => deploy::execute_upload(args, &output).await,
        Commands::Start(args) => deploy::execute_start(args, &output).await,
        Commands::Deploy(args) => deploy::execute_deploy(args, &output).await,
        Commands::Serve(args) => serve::execute(args, &output).await,
        Commands::Run(args) => run::execute(args, &output).await,
        Commands::DbStatus(args) => db_status::execute(args, &output).await,
    };

    // Handle result
    match result {
        Ok(_) => process::exit(0),
        Err(e) => {
            output.error(&format!("Error: {}", e));
            if cli.verbose {
                output.error(&format!("Debug: {:?}", e));
            }
            process::exit(1);
        }
    }
}

fn init_logging(verbose: bool) {
    let filter = if verbose {
        EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("runagent=debug,runagent_cli=debug"))
    } else {
        EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("runagent=info,runagent_cli=info"))
    };

    let subscriber = FmtSubscriber::builder()
        .with_env_filter(filter)
        .with_target(verbose)
        .finish();

    tracing::subscriber::set_global_default(subscriber)
        .expect("Failed to set tracing subscriber");
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    #[test]
    fn verify_cli() {
        Cli::command().debug_assert()
    }

    #[test]
    fn test_cli_parsing() {
        // Test basic command parsing
        let cli = Cli::try_parse_from(&["runagent", "serve", "."]);
        assert!(cli.is_ok());

        // Test with flags
        let cli = Cli::try_parse_from(&["runagent", "--verbose", "serve", ".", "--port", "8450"]);
        assert!(cli.is_ok());
    }
}