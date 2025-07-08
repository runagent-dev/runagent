//! Run command implementation
//!
//! Executes agents with flexible configuration options, supporting both
//! local and remote execution with streaming capabilities.

use crate::utils::output::CliOutput;
use anyhow::{Context, Result};
use futures_util::stream::StreamExt;
use clap::Args;
use runagent::{
    client::RunAgentClient,
    types::RunAgentResult,
};
use serde_json::Value;
use std::collections::HashMap;
use std::path::PathBuf;
// Bring the StreamExt trait into scope so `.next().await` works:
use futures_util::stream::StreamExt;

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

    // Parse extra parameters
    let input_params = parse_input_params(&args, output)?;

    // Display configuration
    display_configuration(&args, &input_params, output)?;

    // Create client and execute
    let client = create_client(&args, output).await?;
    execute_agent(&client, &args, &input_params, output).await?;

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

async fn create_client(
    args: &RunArgs,
    output: &CliOutput,
) -> Result<RunAgentClient> {
    let entrypoint_tag = if args.generic_stream { "generic_stream" } else { "generic" };

    let client = if let Some(ref agent_id) = args.id {
        output.debug(&format!("Creating client for agent ID: {}", agent_id));
        RunAgentClient::new(agent_id, entrypoint_tag, args.local)
            .await
            .context("Failed to create client with agent ID")?
    } else {
        let host = args.host.as_ref().unwrap();
        let port = args.port.unwrap();
        output.debug(&format!("Creating client for {}:{}", host, port));
        RunAgentClient::with_address(
            "direct-connection",
            entrypoint_tag,
            args.local,
            Some(host),
            Some(port),
        )
        .await
        .context("Failed to create client with host/port")?
    };

    Ok(client)
}

async fn execute_agent(
    client: &RunAgentClient,
    args: &RunArgs,
    input_params: &HashMap<String, Value>,
    output: &CliOutput,
) -> Result<()> {
    let input_kwargs: Vec<(&str, Value)> = input_params
        .iter()
        .map(|(k, v)| (k.as_str(), v.clone()))
        .collect();

    if args.generic_stream {
        output.info("▶️ Starting streaming execution...");
        let mut stream = client
            .run_stream(&input_kwargs)
            .await
            .context("Failed to start streaming execution")?;

        let mut chunk_count = 0;
        while let Some(chunk_result) = stream.next().await {
            match chunk_result {
                Ok(data) => {
                    chunk_count += 1;
                    output.info(&format!(
                        "📦 Chunk {}: {}",
                        chunk_count,
                        serde_json::to_string_pretty(&data)
                            .unwrap_or_else(|_| format!("{:?}", data))
                    ));
                }
                Err(e) => {
                    output.error(&format!("Stream error: {}", e));
                    return Err(e.into());
                }
            }
        }

        output.success(&format!(
            "✅ Streaming completed ({} chunks received)",
            chunk_count
        ));
    } else {
        output.info("▶️ Executing agent...");
        let start_time = std::time::Instant::now();

        let result: RunAgentResult = client
            .run(&input_kwargs)
            .await
            .context("Failed to execute agent")?;

        let duration = start_time.elapsed();
        output.success("✅ Execution completed!");
        output.config_item("Duration", &format!("{:.2}s", duration.as_secs_f64()));
        output.separator();

        println!(
            "{}",
            serde_json::to_string_pretty(&result)
                .unwrap_or_else(|_| format!("{:?}", result))
        );
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use std::io::Write;

    #[test]
    fn test_validate_args_both_id_and_host_port() {
        let args = RunArgs {
            id: Some("test-agent".to_string()),
            host: Some("localhost".to_string()),
            port: Some(8450),
            input: None,
            local: false,
            generic: true,
            generic_stream: false,
            timeout: None,
            extra_params: vec![],
        };
        assert!(validate_args(&args).is_err());
    }

    #[test]
    fn test_validate_args_missing_port() {
        let args = RunArgs {
            id: None,
            host: Some("localhost".to_string()),
            port: None,
            input: None,
            local: false,
            generic: true,
            generic_stream: false,
            timeout: None,
            extra_params: vec![],
        };
        assert!(validate_args(&args).is_err());
    }

    #[test]
    fn test_parse_extra_params() {
        let args = RunArgs {
            id: Some("test".to_string()),
            host: None,
            port: None,
            input: None,
            local: false,
            generic: true,
            generic_stream: false,
            timeout: None,
            extra_params: vec![
                "message=hello".to_string(),
                "count=42".to_string(),
                "data={\"key\":\"value\"}".to_string(),
            ],
        };
        let output = CliOutput::new(false);
        let params = parse_input_params(&args, &output).unwrap();
        assert_eq!(params.get("message"), Some(&Value::String("hello".to_string())));
        assert_eq!(params.get("count"), Some(&Value::String("42".to_string())));
        assert!(params.contains_key("data"));
    }

    #[test]
    fn test_parse_input_file() {
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, r#"{{"message": "hello", "count": 42}}"#).unwrap();
        let args = RunArgs {
            id: Some("test".to_string()),
            host: None,
            port: None,
            input: Some(temp_file.path().to_path_buf()),
            local: false,
            generic: true,
            generic_stream: false,
            timeout: None,
            extra_params: vec![],
        };
        let output = CliOutput::new(false);
        let params = parse_input_params(&args, &output).unwrap();
        assert_eq!(params.get("message"), Some(&Value::String("hello".to_string())));
        assert_eq!(params.get("count"), Some(&Value::Number(serde_json::Number::from(42))));
    }

    #[test]
    fn test_invalid_extra_param_format() {
        let args = RunArgs {
            id: Some("test".to_string()),
            host: None,
            port: None,
            input: None,
            local: false,
            generic: true,
            generic_stream: false,
            timeout: None,
            extra_params: vec!["invalid_format".to_string()],
        };
        let output = CliOutput::new(false);
        assert!(parse_input_params(&args, &output).is_err());
    }
}
