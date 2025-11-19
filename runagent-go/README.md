## RunAgent Go SDK

The Go SDK mirrors the Python CLI client so Go services can trigger hosted or local RunAgent deployments. It wraps the `/api/v1/agents/{agent_id}/run` and `/run-stream` endpoints, handles auth/discovery, and translates responses into Go-friendly types.

---

### Feature Overview

- Native Go arguments:
  - Positional: `Arg(...)`, `Args(...)`
  - Keyword: `Kw(k, v)`, `Kws(map[string]any)`
  - Structs become kwargs via `json` tags
  - Single primitives become a single positional arg
- Streaming and non-streaming guardrails:
  - `Run` rejects `*_stream` tags with a helpful error
  - `RunStream` rejects non-stream tags with a helpful error
- Local vs Remote:
  - Local DB discovery from `~/.runagent/runagent_local.db` (override with `Host`/`Port`)
  - Remote uses `RUNAGENT_BASE_URL` (default `https://backend.run-agent.ai`) and Bearer token
- Authentication:
  - `Authorization: Bearer RUNAGENT_API_KEY` automatically for remote calls
  - WS token fallback `?token=...` for streams
- Error taxonomy:
  - `AUTHENTICATION_ERROR`, `CONNECTION_ERROR`, `VALIDATION_ERROR`, `SERVER_ERROR`, `UNKNOWN_ERROR`
  - Execution errors include `Code`, `Suggestion`, `Details` when provided by backend
- Architecture:
  - `GetArchitecture(ctx)` normalizes envelope and legacy formats and enforces `ARCHITECTURE_MISSING` when needed
- Config precedence:
  - Explicit `Config` fields → environment → defaults
- Extra params:
  - `Config.ExtraParams` stored and retrievable via `client.ExtraParams()`

---

### Installation

```bash
go get github.com/runagent-dev/runagent/runagent-go/runagent
```

Requires Go 1.21+.

---

### Configuration Precedence

1. Explicit `runagent.Config` fields  
2. Environment variables  
   - `RUNAGENT_API_KEY`  
   - `RUNAGENT_BASE_URL` (defaults to `https://backend.run-agent.ai`)  
   - `RUNAGENT_LOCAL`, `RUNAGENT_HOST`, `RUNAGENT_PORT`, `RUNAGENT_TIMEOUT`  
3. Library defaults (e.g., local DB discovery, 300 s timeout)

When `Local` is true (or `RUNAGENT_LOCAL=true`), the SDK reads `~/.runagent/runagent_local.db` to discover the host/port unless they’re provided directly.

---

### Local vs Remote: Host/Port Optionality

- Remote (cloud or self-hosted base URL):
  - Do not set `Host`/`Port`. Provide `APIKey` (or set `RUNAGENT_API_KEY`), and optionally `BaseURL`.
  - Example:
    ```go
    client, _ := runagent.NewRunAgentClient(runagent.Config{
        AgentID:       "id",
        EntrypointTag: "minimal",
        APIKey:        os.Getenv("RUNAGENT_API_KEY"),
        // BaseURL optional; defaults to https://backend.run-agent.ai
    })
    ```
- Local:
  - `Host`/`Port` are optional. If either is missing, the SDK discovers the value(s) from `~/.runagent/runagent_local.db` for the given `AgentID`.
  - If discovery fails (agent not registered), you’ll get a clear `VALIDATION_ERROR` suggesting to pass `Host`/`Port` or register the agent locally.
  - Examples:
    ```go
    // Rely fully on DB discovery (no host/port)
    client, _ := runagent.NewRunAgentClient(runagent.Config{
        AgentID: "local-id",
        EntrypointTag: "generic",
        Local: runagent.Bool(true),
    })
    // Provide only Host, let Port be discovered
    client, _ = runagent.NewRunAgentClient(runagent.Config{
        AgentID: "local-id",
        EntrypointTag: "generic",
        Local: runagent.Bool(true),
        Host: "127.0.0.1",
    })
    ```

---

### Quickstart (Remote)

```go
package main

import (
    "context"
    "fmt"
    "time"
    "os"

    "github.com/runagent-dev/runagent/runagent-go/runagent"
)

func main() {
    client, err := runagent.NewRunAgentClient(runagent.Config{
        AgentID:       "YOUR_AGENT_ID",
        EntrypointTag: "minimal",
        APIKey:        os.Getenv("RUNAGENT_API_KEY"),
    })
    if err != nil {
        panic(err)
    }

    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
    defer cancel()

    result, err := client.Run(ctx, runagent.Kw("message", "Summarize Q4 retention metrics"))
    if err != nil {
        panic(err)
    }
    fmt.Printf("Response: %#v\n", result)
}
```

---

### Quickstart (Local)

```go
client, err := runagent.NewRunAgentClient(runagent.Config{
    AgentID:       "local-agent-id",
    EntrypointTag: "generic",
    Local:         runagent.Bool(true),
    Host:          "127.0.0.1", // optional: falls back to DB entry
    Port:          8450,
})
```

If `Host`/`Port` are omitted, the SDK looks up the agent in `~/.runagent/runagent_local.db`. Missing entries yield a helpful `VALIDATION_ERROR`.

---

### Streaming Responses

```go
stream, err := client.RunStream(ctx, runagent.Kw("prompt", "Stream a haiku about Go"))
if err != nil {
    log.Fatal(err)
}
defer stream.Close()

for {
    // Panic with a friendly message on errors (quickstart ergonomics)
    chunk := stream.NextOrPanic(ctx)
    fmt.Print(chunk)
}
```

- Local streams connect to `ws://{host}:{port}/api/v1/agents/{id}/run-stream`.  
- Remote streams upgrade to `wss://backend.run-agent.ai/api/v1/...` and append `?token=RUNAGENT_API_KEY`.

---

### Extra Params & Metadata

`Config.ExtraParams` accepts arbitrary metadata; call `client.ExtraParams()` to retrieve a copy. Reserved for future features (tracing, tags) without breaking the API.

---

### Error Handling

All SDK errors satisfy `error` and expose a concrete `*runagent.RunAgentError`:

| Type | Meaning | Typical Fix |
| --- | --- | --- |
| `AUTHENTICATION_ERROR` | API key missing/invalid | Set `RUNAGENT_API_KEY` or `Config.APIKey` |
| `CONNECTION_ERROR` | Network/DNS/TLS issues | Verify network, agent uptime |
| `VALIDATION_ERROR` | Bad config or missing agent | Check `agent_id`, entrypoint, local DB |
| `SERVER_ERROR` | Upstream failure (5xx) | Retry or inspect agent logs |

Remote responses that return a structured `error` block become `RunAgentExecutionError` with `Code`, `Suggestion`, and `Details` copied directly.

Use `errors.As(err, &runErr)` to inspect fields.

---

### Testing & Troubleshooting

- `go test ./runagent/...` exercises the SDK build.
- Enable debug logging in your application to capture request IDs.
- For local issues, run `runagent cli agents list` to confirm the SQLite database contains the agent and the host/port match.
- For remote failures, confirm the agent is deployed and the entrypoint tag is enabled in the RunAgent Cloud dashboard.

---

### Publishing

See `PUBLISH.md` in this directory for release instructions (version bumps, tagging, and module proxy propagation).

