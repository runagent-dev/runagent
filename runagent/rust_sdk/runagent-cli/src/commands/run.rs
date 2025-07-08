//! Run command implementation

use crate::utils::output::CliOutput;
use anyhow::{Context, Result};
use clap::Args;
use std::collections::HashMap;
use std::path::PathBuf;
use serde_json::Value;

/// Run an agent with flexible configuration options
#[derive(Args)]
pub struct RunArgs {
    /// Agent ID to run
    #[arg(long, short)]
    id: Option<String>,

    /// Host to connect to (use with --port)
    #[arg(long)]
    host: Option<String>,

    /// Port to connect to (use with --host)
    #[arg(long)]
    port: Option<u16>,

    /// Path to input JSON file
    #[arg(long)]
    input: Option<PathBuf>,

    /// Run agent locally
    #[arg(long)]
    local: bool,

    /// Use generic mode (default)
    #[arg(long)]
    generic: bool,

    /// Use generic streaming mode
    #[arg(long, name = "generic-stream")]
    generic_stream: bool,

    /// Timeout in seconds
    #[arg(long)]
    timeout: Option<u64>,

    /// Extra parameters in key=value format
    #[arg(trailing_var_arg = true)]
    extra_params: Vec<String>,
}

pub async fn execute(args: RunArgs, output: &CliOutput) -> Result<()> {
    // Validate arguments
    validate_args(&args)?;

    // Parse input parameters
    let input_params = parse_input_params(&args, output)?;

    // Display configuration
    display_configuration(&args, &input_params, output)?;

    // Mock execution since we don't have the full client implementation yet
    mock_execute_agent(&args, &input_params, output).await?;

    Ok(())
}

fn validate_args(args: &RunArgs) -> Result<()> {
    // Either agent-id OR host/port must be provided
    let agent_id_provided = args.id.is_some();
    let host_port_provided = args.host.is_some() || args.port.is_some();

    if agent_id_provided && host_port_provided {
        return Err(anyhow::anyhow!(
            "Cannot specify both --id and --host/--port. Choose one approach."
        ));
    }

    if !agent_id_provided && !host_port_provided {
        return Err(anyhow::anyhow!(
            "Must specify either --id or both --host and --port."
        ));
    }

    // If using host/port, both must be provided
    if host_port_provided && (args.host.is_none() || args.port.is_none()) {
        return Err(anyhow::anyhow!(
            "When using host/port, both --host and --port must be specified."
        ));
    }

    // Generic mode validation
    if args.generic && args.generic_stream {
        return Err(anyhow::anyhow!(
            "Cannot specify both --generic and --generic-stream. Choose one."
        ));
    }

    // Input file OR extra params, not both
    if args.input.is_some() && !args.extra_params.is_empty() {
        return Err(anyhow::anyhow!(
            "Cannot specify both --input file and extra parameters. Use either --input config.json OR --key=value..."
        ));
    }

    Ok(())
}

fn parse_input_params(
    args: &RunArgs,
    output: &CliOutput,
) -> Result<HashMap<String, Value>> {
    if let Some(ref input_file) = args.input {
        // Load from JSON file
        let content = std::fs::read_to_string(input_file)
            .with_context(|| format!("Failed to read input file: {}", input_file.display()))?;
        let params: HashMap<String, Value> = serde_json::from_str(&content)
            .with_context(|| format!("Invalid JSON in input file: {}", input_file.display()))?;
        output.info(&format!("📄 Loaded input from: {}", input_file.display()));
        Ok(params)
    } else if !args.extra_params.is_empty() {
        // Parse extra parameters
        let mut params = HashMap::new();
        for param in &args.extra_params {
            if let Some((key, value)) = param.split_once('=') {
                let json_value = serde_json::from_str(value)
                    .unwrap_or_else(|_| Value::String(value.to_string()));
                params.insert(key.to_string(), json_value);
            } else {
                return Err(anyhow::anyhow!(
                    "Invalid parameter format: '{}'. Use --key=value format.", param
                ));
            }
        }
        Ok(params)
    } else {
        output.warning("⚠️ No input file or extra parameters provided. Running with defaults.");
        Ok(HashMap::new())
    }
}

fn display_configuration(
    args: &RunArgs,
    input_params: &HashMap<String, Value>,
    output: &CliOutput,
) -> Result<()> {
    output.info("🚀 RunAgent Configuration:");

    // Connection info
    if let Some(ref agent_id) = args.id {
        output.config_item("Agent ID", agent_id);
    } else {
        output.config_item("Host", args.host.as_ref().unwrap());
        output.config_item("Port", &args.port.unwrap().to_string());
    }

    // Mode
    let mode = if args.generic_stream {
        "Generic Streaming"
    } else {
        "Generic"
    };
    output.config_item("Mode", mode);

    // Local execution
    if args.local {
        output.config_item("Local", "Yes");
    }

    // Timeout
    if let Some(timeout) = args.timeout {
        output.config_item("Timeout", &format!("{}s", timeout));
    }

    // Input configuration
    if let Some(ref input_file) = args.input {
        output.config_item("Input file", &input_file.display().to_string());
        output.config_item(
            "Config keys",
            &format!("{:?}", input_params.keys().collect::<Vec<_>>()),
        );
    } else if !input_params.is_empty() {
        output.info("   Extra parameters:");
        for (key, value) in input_params {
            let value_str = match value {
                Value::String(s) => s.clone(),
                _ => serde_json::to_string(value).unwrap_or_default(),
            };
            output.config_item(&format!("     --{}", key), &value_str);
        }
    }

    Ok(())
}

// Mock execution for now - replace with real implementation later
async fn mock_execute_agent(
    args: &RunArgs,
    input_params: &HashMap<String, Value>,
    output: &CliOutput,
) -> Result<()> {
    if args.generic_stream {
        output.info("▶️ Starting streaming execution...");
        
        // Mock streaming chunks
        for i in 1..=5 {
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
            output.info(&format!("📦 Chunk {}: Mock streaming data", i));
        }
        
        output.success("✅ Streaming completed (5 chunks received)");
    } else {
        output.info("▶️ Executing agent...");
        let start_time = std::time::Instant::now();
        
        // Mock execution delay
        tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
        
        let duration = start_time.elapsed();
        output.success("✅ Execution completed!");
        output.config_item("Duration", &format!("{:.2}s", duration.as_secs_f64()));
        
        // Mock result
        let result = serde_json::json!({
            "success": true,
            "result": "Mock execution result",
            "input_params": input_params,
            "timestamp": chrono::Utc::now().to_rfc3339()
        });
        
        println!("{}", serde_json::to_string_pretty(&result)?);
    }

    Ok(())
}