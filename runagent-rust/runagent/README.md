# RunAgent Rust SDK

[![Crates.io](https://img.shields.io/crates/v/runagent.svg)](https://crates.io/crates/runagent)
[![Docs](https://docs.rs/runagent/badge.svg)](https://docs.rs/runagent)
[![Build Status](https://github.com/runagent-dev/runagent/workflows/CI/badge.svg)](https://github.com/runagent-dev/runagent/actions)

Rust bindings for the RunAgent platform. Use it to call agents you deploy with the CLI—whether they run locally on your laptop or remotely on `backend.run-agent.ai`.

---

## Installation

```bash
cargo add runagent tokio serde_json futures
```

```toml
[dependencies]
runagent = "0.1"
tokio = { version = "1.35", features = ["full"] }
serde_json = "1.0"
futures = "0.3"
```

---

## Configuration Overview

The SDK uses a single constructor pattern. All configuration is done through `RunAgentClientConfig`:

```rust
use runagent::RunAgentClientConfig;

// Local agent with explicit address
let client = RunAgentClient::new(
    RunAgentClientConfig::new("agent-id", "entrypoint")
        .with_local(true)
        .with_address("127.0.0.1", 8450)
        .with_enable_registry(false)
).await?;

// Remote agent
let client = RunAgentClient::new(
    RunAgentClientConfig::new("agent-id", "entrypoint")
        .with_api_key(env::var("RUNAGENT_API_KEY").unwrap())
).await?;
```

| Setting         | Cloud            | Local (auto discovery) | Local (explicit)  |
|-----------------|------------------|------------------------|-------------------|
| `local`         | `false` (default) | `true`                 | `true`            |
| Host / Port     | derived from URL | looked up via SQLite   | `with_address()`  |
| Base URL        | `RUNAGENT_BASE_URL` \|\| default | n/a | n/a                |
| API Key         | `RUNAGENT_API_KEY` (required) | optional | optional          |
| Registry        | n/a              | `true` (default)       | `false`           |

- `RUNAGENT_API_KEY`: Bearer token for remote agents (can be set via env var or `with_api_key()`).
- `RUNAGENT_BASE_URL`: Override the default cloud endpoint (e.g. staging).
- For local discovery, install the crate with the `db` feature and ensure the CLI has registered the agent in `~/.runagent/runagent_local.db`.

---

## Usage

### Sync (Blocking) - Simplest

#### Non-streaming

```rust
use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

fn main() -> runagent::RunAgentResult<()> {
    // Direct struct construction
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: "agent-id".to_string(),
        entrypoint_tag: "entrypoint".to_string(),
        api_key: Some("your-api-key".to_string()),
        base_url: Some("http://localhost:8333/".to_string()),
        ..RunAgentClientConfig::default() // Omits None values
    })?;

    let response = client.run(&[("message", json!("Hello!"))])?;
    println!("Response: {}", response);
    Ok(())
}
```

#### Streaming

```rust
use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

fn main() -> runagent::RunAgentResult<()> {
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: "agent-id".to_string(),
        entrypoint_tag: "entrypoint_stream".to_string(),
        api_key: Some("your-api-key".to_string()),
        ..RunAgentClientConfig::default()
    })?;

    // Streaming collects all chunks into a vector
    let chunks = client.run_stream(&[("message", json!("Hello!"))])?;
    for chunk in chunks {
        println!(">> {}", chunk?);
    }
    Ok(())
}
```

### Async (Recommended)

#### Non-streaming

```rust
use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    // Direct struct construction
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: "agent-id".to_string(),
        entrypoint_tag: "entrypoint".to_string(),
        api_key: Some("your-api-key".to_string()),
        base_url: Some("http://localhost:8333/".to_string()),
        ..RunAgentClientConfig::default()
    }).await?;

    let response = client.run(&[("message", json!("Hello!"))]).await?;
    println!("Response: {}", response);
    Ok(())
}
```

#### Streaming

```rust
use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: "agent-id".to_string(),
        entrypoint_tag: "entrypoint_stream".to_string(),
        api_key: Some("your-api-key".to_string()),
        ..RunAgentClientConfig::default()
    }).await?;

    // Real streaming - processes chunks as they arrive
    let mut stream = client.run_stream(&[("message", json!("Hello!"))]).await?;
    while let Some(chunk) = stream.next().await {
        println!(">> {}", chunk?);
    }
    Ok(())
}
```

### Alternative: Builder Pattern

You can also use the builder pattern instead of direct struct construction:

```rust
use runagent::{RunAgentClient, RunAgentClientConfig};

// Async
let client = RunAgentClient::new(
    RunAgentClientConfig::new("agent-id", "entrypoint")
        .with_api_key("your-api-key")
        .with_base_url("http://localhost:8333/")
).await?;

// Sync
use runagent::blocking::RunAgentClient;
let client = RunAgentClient::new(
    RunAgentClientConfig::new("agent-id", "entrypoint")
        .with_api_key("your-api-key")
        .with_base_url("http://localhost:8333/")
)?;
```

### Local Agents

#### With explicit address

```rust
use runagent::{RunAgentClient, RunAgentClientConfig};

let client = RunAgentClient::new(RunAgentClientConfig {
    agent_id: "local-agent-id".to_string(),
    entrypoint_tag: "minimal".to_string(),
    local: Some(true),
    host: Some("127.0.0.1".to_string()),
    port: Some(8452),
    enable_registry: Some(false), // Skip DB lookup
    ..RunAgentClientConfig::default()
}).await?;
```

#### With auto-discovery (requires `db` feature)

```rust
let client = RunAgentClient::new(RunAgentClientConfig {
    agent_id: "local-agent-id".to_string(),
    entrypoint_tag: "minimal".to_string(),
    local: Some(true),
    // enable_registry defaults to true for local agents
    ..RunAgentClientConfig::default()
}).await?;
```

> **Guardrails**: tags ending with `_stream` can only be run via `run_stream*`. Non-stream tags must be run via `run*`. The client raises clear errors (`STREAM_ENTRYPOINT`, `NON_STREAM_ENTRYPOINT`) with suggestions.

---

## Architecture Expectations

During initialization the client calls `/api/v1/agents/{id}/architecture` and expects the envelope:

```json
{
  "success": true,
  "data": {
    "agent_id": "…",
    "entrypoints": [
      { "tag": "minimal", "file": "main.py", "module": "run", "extractor": {} }
    ]
  },
  "message": "Agent architecture retrieved successfully",
  "error": null,
  "timestamp": "…",
  "request_id": "…"
}
```

- If `success === false` we propagate `error.code/message/suggestion/details`.
- If `data.entrypoints` is missing we raise `ARCHITECTURE_MISSING`.
- When an entrypoint can’t be found we log the list returned by the server to help debug typos.

---

## API Reference

### Client Creation

| Method | Description |
|--------|-------------|
| `RunAgentClient::new(config: RunAgentClientConfig)` | Single constructor for all client types. |

### Configuration Builder

| Method | Description |
|--------|-------------|
| `RunAgentClientConfig::new(agent_id, entrypoint_tag)` | Create config with required fields. |
| `.with_local(bool)` | Set local flag (default: `false`). |
| `.with_address(host, port)` | Set explicit host/port for local agents. |
| `.with_api_key(key)` | Set API key (overrides env var). |
| `.with_base_url(url)` | Override default base URL. |
| `.with_enable_registry(bool)` | Enable/disable database lookup (default: `true` for local). |
| `.with_extra_params(params)` | Set extra parameters for future use. |

### Client Methods

| Method | Description |
|--------|-------------|
| `run` / `run_with_args` | Execute non-streaming entrypoints. |
| `run_stream` / `run_stream_with_args` | Execute streaming entrypoints (async stream of `Value`). |
| `health_check` | Check if the agent is reachable. |
| `get_agent_architecture` | Fetch the normalized architecture (see above). |

All methods return `RunAgentResult<T>` where `RunAgentError::Execution { code, message, suggestion, details }` carries actionable metadata (e.g. `AGENT_NOT_FOUND_REMOTE`, `STREAM_ENTRYPOINT`, `AUTHENTICATION_ERROR`). Inspect these fields to guide users.

---

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| `STREAM_ENTRYPOINT` | Call `run_stream*` or switch to a non-stream tag. |
| `NON_STREAM_ENTRYPOINT` | Call `run*` or deploy a `_stream` entrypoint. |
| `AGENT_NOT_FOUND_LOCAL` | Ensure the agent is registered locally (`runagent serve` or `runagent config --register-agent`). |
| `AGENT_NOT_FOUND_REMOTE` | Verify the agent ID and that your API key has access. |
| `AUTHENTICATION_ERROR` | Set `RUNAGENT_API_KEY` env var or use `.with_api_key()` in config. |
| `ARCHITECTURE_MISSING` | Redeploy the agent; ensure entrypoints are defined in `runagent.config.json`. |

---

## Security Best Practices

- Never hardcode API keys; use env vars or secret managers.
- For browser/edge bridging, proxy calls through your backend rather than exposing long-lived keys.
- When running locally, restrict access to `~/.runagent/runagent_local.db`.

---

## Development & Publishing

```bash
cargo fmt
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

To publish a new release, follow [`../PUBLISH.md`](../PUBLISH.md) (version bump, `cargo package`, `cargo publish`, tag release).

---

## Need Help?

- Docs: `docs/sdk/rust/` (coming soon) or https://docs.rs/runagent
- Issues: [github.com/runagent-dev/runagent/issues](https://github.com/runagent-dev/runagent/issues)
- Community: Discord link in the main repo README
- Commercial support: contact the RunAgent team via the dashboard
