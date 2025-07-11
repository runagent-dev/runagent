# RunAgent Rust SDK

[![Crates.io](https://img.shields.io/crates/v/runagent.svg)](https://crates.io/crates/runagent)
[![Documentation](https://docs.rs/runagent/badge.svg)](https://docs.rs/runagent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/runagent-dev/runagent/workflows/CI/badge.svg)](https://github.com/runagent-dev/runagent/actions)

---

## 🎯 What is RunAgent?

RunAgent is a comprehensive Rust SDK for deploying and managing AI agents with support for multiple frameworks including **LangChain**, **LangGraph**, **LlamaIndex**, and more. Whether you're building chatbots, autonomous agents, or complex AI workflows, RunAgent provides the tools you need to deploy, test, and scale your AI applications.

---

## ✨ Features

- 🤖 **Multi-Framework Support**: LangChain, LangGraph, LlamaIndex, Letta, CrewAI, AutoGen
- 🚀 **Local & Remote Deployment**: Deploy agents locally or to remote servers
- ⚡ **Real-time Streaming**: WebSocket-based streaming for real-time interactions
- 💾 **Database Management**: SQLite-based agent metadata and history
- 📋 **Template System**: Pre-built templates for rapid setup
- 🛡️ **Type Safety**: Full Rust type safety with error handling
- 🔄 **Async/Await**: Powered by Tokio for async ops

---

## 📦 Installation

```bash
cargo add runagent tokio
````

Or add manually to `Cargo.toml`:

```toml
[dependencies]
runagent = "0.1.0"
tokio = { version = "1.35", features = ["full"] }
```

---

## 🏃 Quick Start

### ✅ Basic Agent Interaction

```rust
use runagent::prelude::*;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    runagent::init_logging();
    let client = RunAgentClient::new("my-agent-id", "generic", true).await?;

    let response = client.run(&[
        ("message", json!("Hello, world!")),
        ("temperature", json!(0.7))
    ]).await?;

    println!("Response: {}", response);
    Ok(())
}
```

### 🔁 Streaming Agent Interaction

```rust
use runagent::prelude::*;
use futures::StreamExt;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new("my-agent-id", "generic_stream", true).await?;

    let mut stream = client.run_stream(&[
        ("message", json!("Tell me a story"))
    ]).await?;

    while let Some(chunk) = stream.next().await {
        match chunk {
            Ok(data) => println!("Chunk: {}", data),
            Err(e) => eprintln!("Stream error: {}", e),
        }
    }

    Ok(())
}
```

---

## 🔧 Configuration

### ✅ Environment Variables

```bash
# API Configuration
export RUNAGENT_API_KEY="your-api-key"
export RUNAGENT_BASE_URL="https://api.runagent.ai"

# Local Configuration
export RUNAGENT_CACHE_DIR="~/.runagent"
export RUNAGENT_LOGGING_LEVEL="info"
```

### ✅ Configuration Builder

```rust
use runagent::RunAgentConfig;

let config = RunAgentConfig::new()
    .with_api_key("your-api-key")
    .with_base_url("https://api.runagent.ai")
    .with_logging()
    .build();
```

---

## 🎯 Framework-Specific Examples

### LangChain Integration

```rust
use runagent::prelude::*;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new("langchain-agent", "invoke", true).await?;

    let response = client.run(&[
        ("input", json!({
            "messages": [
                {"role": "user", "content": "What is the weather like?"}
            ]
        }))
    ]).await?;

    println!("LangChain response: {}", response);
    Ok(())
}
```

### LangGraph Workflows

```rust
use runagent::prelude::*;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new("langgraph-agent", "stream", true).await?;

    let mut stream = client.run_stream(&[
        ("input", json!({
            "messages": [{"role": "user", "content": "Analyze this data"}]
        }))
    ]).await?;

    while let Some(chunk) = stream.next().await {
        match chunk {
            Ok(data) => {
                if let Some(node) = data.get("node") {
                    println!("Executing node: {}", node);
                }
            }
            Err(e) => eprintln!("Error: {}", e),
        }
    }

    Ok(())
}
```

---

## 🏗️ Architecture

### Core Components

* **Client**: High-level client for agent interaction
* **Server**: FastAPI-like local server for testing
* **Database**: SQLite-based agent history store
* **Framework Executors**: Executors for LangChain, LangGraph, etc.
* **Serialization**: Safe messaging via WebSocket

### Optional Features

Enable or disable features in `Cargo.toml`:

```toml
[dependencies]
runagent = { version = "0.1.0", features = ["db", "server"] }
```

Available:

* `db` (default): Enable database support
* `server` (default): Enable local server

---

## 📚 API Reference

### `RunAgentClient`

* `new(agent_id, entrypoint_tag, local)`
* `run(input_kwargs)`
* `run_stream(input_kwargs)`
* `health_check()`

### `LocalServer`

* `new(agent_id, agent_path, host, port)`
* `from_path(agent_path, host, port)`
* `start()`
* `get_info()`

### `DatabaseService`

* `new(db_path)`
* `add_agent(agent)`
* `list_agents()`
* `get_capacity_info()`

---

## 🔍 Error Handling

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
            if err.is_retryable() {
                retry_operation()
            } else {
                Err(err)
            }
        }
        Err(e) => Err(e),
    }
}
```

---

## 🧪 Testing

```bash
cargo test
cargo test --all-features
cargo test --test integration
```

---

## 📖 Examples

See `examples/` folder for:

* ✅ Basic usage
* 🔁 Streaming
* 💾 Database
* 🌐 Server setup
* 🎯 Framework integrations

---

## 🤝 Contributing

We welcome contributions! See `CONTRIBUTING.md` for guidelines.

### Development Setup

```bash
git clone https://github.com/runagent-dev/runagent.git
cd runagent/runagent-rust
cargo build
cargo test
```

---

## 📋 Roadmap

* Python interop via PyO3
* Additional framework support
* Enhanced streaming
* Production deployment tools
* Monitoring & observability
* CLI tool integration

---

## 🔗 Links

* 🌍 [Website](https://runagent.dev)
* 📚 [Documentation](https://docs.runagent.dev)
* 💻 [Repository](https://github.com/runagent-dev/runagent)
* ❓ [Issues](https://github.com/runagent-dev/runagent/issues)
* 🐍 [Python SDK](https://pypi.org/project/runagent/)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file.

---

## 🙏 Acknowledgments

* Built with [Tokio](https://tokio.rs)
* Uses [Axum](https://github.com/tokio-rs/axum)
* SQL powered by [SQLx](https://github.com/launchbadge/sqlx)
* WebSocket support via [tokio-tungstenite](https://github.com/snapview/tokio-tungstenite)

---

Need help? Join our [Discord](https://discord.gg/runagent) or check the documentation!


