# RunAgent Rust SDK

[![Crates.io](https://img.shields.io/crates/v/runagent.svg)](https://crates.io/crates/runagent)
[![Documentation](https://docs.rs/runagent/badge.svg)](https://docs.rs/runagent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/runagent-dev/runagent/workflows/CI/badge.svg)](https://github.com/runagent-dev/runagent/actions)

---

## What is RunAgent?

RunAgent is a comprehensive Rust SDK for deploying and managing AI agents with support for multiple frameworks including **LangChain**, **LangGraph**, **LlamaIndex**, and more. Whether you're building chatbots, autonomous agents, or complex AI workflows, RunAgent provides the tools you need to deploy, test, and scale your AI applications.

---

## Features

- **Multi-Framework Support**: LangChain, LangGraph, LlamaIndex, Letta, CrewAI, AutoGen
- **Local & Remote Deployment**: Deploy agents locally or to remote servers
- **Real-time Streaming**: WebSocket-based streaming for real-time interactions
- **Database Management**: SQLite-based agent metadata and history
- **Template System**: Pre-built templates for rapid setup
- **Type Safety**: Full Rust type safety with error handling
- **Async/Await**: Powered by Tokio for async operations

---

## Installation

```bash
cargo add runagent tokio
```

Or add manually to `Cargo.toml`:

```toml
[dependencies]
runagent = "0.1.0"
tokio = { version = "1.35", features = ["full"] }
serde_json = "1.0"
futures = "0.3"
```

---

## Quick Start

> **RunAgent Cloud** is the recommended way to get started. Deploy and interact with agents hosted on RunAgent's infrastructure without managing your own servers.

### RunAgent Cloud

RunAgent Cloud allows you to deploy and interact with agents hosted on RunAgent's infrastructure. This is the recommended way to get started quickly.

**Key Benefits:**
- No server setup required
- Automatic scaling
- Managed infrastructure
- Simple authentication via API key

#### Step 1: Set Up Authentication

**Important:** You must export your API key before running your application:

```bash
export RUNAGENT_API_KEY="your-api-key"
```

You can get your API key from the [RunAgent Dashboard](https://runagent.dev).

#### Step 2: Connect to Your Agent

When connecting to RunAgent Cloud, set `local = false`:

```rust
use runagent::client::RunAgentClient;

let client = RunAgentClient::new(
    "your-agent-id",      // Your agent ID from RunAgent Cloud
    "agno_print_response", // Entrypoint tag
    false                  // local = false for cloud
).await?;
```

#### Step 3: Run Your Agent

**Non-Streaming Example:**

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Set RUNAGENT_API_KEY environment variable before running
    let agent_id = "your-agent-id";
    
    // Connect to cloud agent (local = false)
    let client = RunAgentClient::new(agent_id, "agno_print_response", false).await?;
    
    // Run with positional and keyword arguments
    let response = client.run_with_args(
        &[json!("Write small paragraph on how i met your mother tv series")], // positional args
        &[] // no keyword args
    ).await?;
    
    println!("Response: {}", response);
    Ok(())
}
```

**Streaming Example:**

```rust
use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Set RUNAGENT_API_KEY environment variable before running
    let agent_id = "your-agent-id";
    
    // Connect to cloud agent with streaming entrypoint
    let client = RunAgentClient::new(agent_id, "agno_print_response_stream", false).await?;
    
    // Run with streaming
    let mut stream = client.run_stream(&[
        ("prompt", json!("is investing in AI is good idea?"))
    ]).await?;
    
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => println!("{}", chunk),
            Err(e) => {
                println!("Error: {}", e);
                break;
            }
        }
    }
    
    Ok(())
}
```

**Complete Workflow:**

```bash
# 1. Export your API key
export RUNAGENT_API_KEY="your-api-key"

# 2. Run your application
cargo run
```

---

### Local Development

For local development, you can run agents on your own machine. Set `local = true` when creating the client.

#### Basic Agent Interaction (Local)

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "your-agent-id";
    
    // Connect to local agent (local = true)
    let client = RunAgentClient::new(agent_id, "lead_score_flow", true).await?;
    
    // Run with keyword arguments only
    let response = client.run_with_args(
        &[], // no positional args
        &[
            ("top_n", json!(1)),
            ("generate_emails", json!(true))
        ]
    ).await?;
    
    println!("Response: {}", serde_json::to_string_pretty(&response)?);
    Ok(())
}
```

### Connecting to Local Agent with Explicit Address

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "your-agent-id";
    
    // Connect to local agent with explicit host and port
    let client = RunAgentClient::with_address(
        agent_id,
        "generic",
        true,
        Some("127.0.0.1"),
        Some(8452)
    ).await?;
    
    let response = client.run(&[
        ("message", json!("Hello, world!"))
    ]).await?;
    
    println!("Response: {}", response);
    Ok(())
}
```

---

## Configuration

### RunAgent Cloud Setup

**Required:** Set your API key as an environment variable before running your application:

```bash
export RUNAGENT_API_KEY="your-api-key"
```

**Optional:** Customize the base URL (defaults to `https://api.runagent.ai`):

```bash
export RUNAGENT_BASE_URL="https://api.runagent.ai"
```

### Local Development Setup

For local development, you can configure cache and logging:

```bash
export RUNAGENT_CACHE_DIR="~/.runagent"
export RUNAGENT_LOGGING_LEVEL="info"
```

### Quick Reference

| Setting | RunAgent Cloud | Local Development |
|---------|---------------|-------------------|
| **API Key** | **Required** (`RUNAGENT_API_KEY`) | Not needed |
| **Base URL** | Optional (defaults to `https://api.runagent.ai`) | Not needed |
| **Client Parameter** | `local = false` | `local = true` |
| **Agent Location** | RunAgent infrastructure | Your local machine |

### Configuration Builder

You can also configure the SDK programmatically:

```rust
use runagent::RunAgentConfig;

let config = RunAgentConfig::new()
    .with_api_key("your-api-key")
    .with_base_url("https://api.runagent.ai")
    .with_logging()
    .build();
```

---

## Architecture

### Core Components

* **Client**: High-level client for agent interaction
* **REST Client**: HTTP-based client for non-streaming requests
* **Socket Client**: WebSocket-based client for streaming interactions
* **Database**: SQLite-based agent history store (optional)
* **Serialization**: Safe messaging via WebSocket

### Optional Features

Enable or disable features in `Cargo.toml`:

```toml
[dependencies]
runagent = { version = "0.1.0", features = ["db"] }
```

Available features:

* `db` (default): Enable database support for local agent management

---

## API Reference

### `RunAgentClient`

Main client for interacting with RunAgent deployments.

#### Methods

* `new(agent_id, entrypoint_tag, local)` - Create a new client
  * `agent_id`: The agent identifier
  * `entrypoint_tag`: The entrypoint function tag (e.g., "agno_print_response")
  * `local`: `true` for local agents, `false` for cloud agents

* `with_address(agent_id, entrypoint_tag, local, host, port)` - Create client with explicit address

* `run(input_kwargs)` - Run agent with keyword arguments only
  * Returns: `RunAgentResult<Value>`

* `run_with_args(input_args, input_kwargs)` - Run agent with both positional and keyword arguments
  * `input_args`: Slice of positional arguments as `Value`
  * `input_kwargs`: Slice of tuples `(&str, Value)` for keyword arguments

* `run_stream(input_kwargs)` - Run agent with streaming response
  * Returns: `RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>>`

* `run_stream_with_args(input_args, input_kwargs)` - Run agent with streaming and both argument types

* `health_check()` - Check if the agent is available

* `get_agent_architecture()` - Get the agent's architecture information

### `DatabaseService`

Database service for managing local agent metadata (requires `db` feature).

* `new(db_path)` - Create a new database service
* `add_agent(agent)` - Add an agent to the database
* `list_agents()` - List all agents in the database
* `get_agent(agent_id)` - Get agent information by ID

---

## Error Handling

```rust
use runagent::{RunAgentError, RunAgentResult};

fn handle_errors() -> RunAgentResult<()> {
    match some_operation() {
        Ok(result) => Ok(result),
        Err(RunAgentError::Authentication { message }) => {
            eprintln!("Auth error: {}", message);
            Err(RunAgentError::authentication("Invalid credentials"))
        }
        Err(RunAgentError::Connection { message }) => {
            eprintln!("Connection error: {}", message);
            Err(RunAgentError::connection("Connection failed"))
        }
        Err(e) => Err(e),
    }
}
```

---

## Testing

```bash
cargo test
cargo test --all-features
cargo test --test integration
```

---

## Examples

See the `examples/` folder for complete examples:

* Basic usage with cloud agents
* Streaming interactions
* Local agent connections
* Framework integrations

---

## Contributing

We welcome contributions! See `CONTRIBUTING.md` for guidelines.

### Development Setup

```bash
git clone https://github.com/runagent-dev/runagent.git
cd runagent/runagent-rust
cargo build
cargo test
```

---

## Roadmap

* Python interop via PyO3
* Additional framework support
* Enhanced streaming capabilities
* Production deployment tools
* Monitoring & observability
* CLI tool integration

---

## Links

* [Website](https://run-agent.ai/)
* [Documentation](https://docs.run-agent.ai/explanation/introduction)
* [Repository](https://github.com/runagent-dev/runagent)
* [Issues](https://github.com/runagent-dev/runagent/issues)
* [Python SDK](https://pypi.org/project/runagent/)

---

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file.

---

## Acknowledgments

* Built with [Tokio](https://tokio.rs)
* Uses [Axum](https://github.com/tokio-rs/axum)
* SQL powered by [SQLx](https://github.com/launchbadge/sqlx)
* WebSocket support via [tokio-tungstenite](https://github.com/snapview/tokio-tungstenite)

---

Need help? Join our [Discord](https://discord.gg/runagent) or check the documentation!


