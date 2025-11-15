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

```rust
RunAgentClient::new(agent_id, entrypoint_tag, local);
RunAgentClient::with_address(agent_id, entrypoint_tag, true, Some("127.0.0.1"), Some(8450));
RunAgentClient::with_remote_config(agent_id, entrypoint_tag, "https://backend.run-agent.ai", Some(api_key));
```

| Setting         | Cloud            | Local (auto discovery) | Local (explicit)  |
|-----------------|------------------|------------------------|-------------------|
| `local`         | `false`          | `true`                 | `true`            |
| Host / Port     | derived from URL | looked up via SQLite   | `with_address`    |
| Base URL        | `RUNAGENT_BASE_URL` \|\| default | n/a | n/a                |
| API Key         | `RUNAGENT_API_KEY` (required) | optional | optional          |

- `RUNAGENT_API_KEY`: Bearer token for remote agents.
- `RUNAGENT_BASE_URL`: Override the default cloud endpoint (e.g. staging).
- For local discovery install the crate with the `db` feature and ensure the CLI has registered the agent in `~/.runagent/runagent_local.db`.

---

## Usage

### Cloud (non-streaming)

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    dotenvy::from_filename("local.env").ok(); // optional

    let client = RunAgentClient::new("agent-id", "support_flow", false).await?;
    let response = client.run(&[("message", json!("Hello!"))]).await?;

    println!("Response: {}", response);
    Ok(())
}
```

### Cloud (streaming)

```rust
use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    let client = RunAgentClient::new("agent-id", "support_flow_stream", false).await?;
    let mut stream = client.run_stream(&[("message", json!("Need help"))]).await?;

    while let Some(chunk) = stream.next().await {
        println!(">> {}", chunk?);
    }

    Ok(())
}
```

### Local (auto discovery)

```rust
let client = RunAgentClient::new("local-agent-id", "minimal", true).await?;
let result = client.run(&[("message", json!("Hello there"))]).await?;
```

### Local (explicit host/port)

```rust
let client = RunAgentClient::with_address(
    "local-agent-id",
    "minimal",
    true,
    Some("127.0.0.1"),
    Some(8450),
).await?;
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

| Method | Description |
|--------|-------------|
| `RunAgentClient::new(agent_id, entrypoint_tag, local)` | Create a client (auto-detect host for local agents if DB feature is enabled). |
| `RunAgentClient::with_address(agent_id, entrypoint_tag, local, host, port)` | Connect to a local agent at a specific address. |
| `RunAgentClient::with_remote_config(agent_id, entrypoint_tag, base_url, api_key)` | Override remote base URL/API key. |
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
| `AUTHENTICATION_ERROR` | Set `RUNAGENT_API_KEY` or pass `api_key` to `with_remote_config`. |
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
