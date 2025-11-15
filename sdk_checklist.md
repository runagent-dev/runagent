## SDK Implementation Guide

### Purpose And Scope
- **Goal**: every SDK (Python, JS/TS, Go, Rust, future C#/Swift/Flutter, etc.) exposes a single `RunAgentClient` class with `run()` and `run_stream()`; Python CLI is the superset, other SDKs only need client functions.
- **Reference implementation**: Python CLI layers on top of the Python SDK. When unsure, mirror the Python behavior and propose parity improvements if features are missing.
- **Separation of concerns**: the CLI covers deployment/orchestration; SDKs focus purely on invoking deployed agents.

### Client Initialization Contract
- **Constructor signature** *(language-idiomatic)*: `RunAgentClient({ agent_id, entrypoint_tag, local?, host?, port?, api_key?, base_url?, extra_params? })`.
- **Required inputs**: `agent_id`, `entrypoint_tag`.
- **Optional inputs**:
  - `local` (default `false` except Python CLI) indicates whether to auto-discover host/port for co-located agents.
  - `host`/`port` override local discovery; required when running on a device that cannot read the local SQLite DB (e.g. browsers, remote SDK consumers).
  - `api_key` overrides environment configuration for cloud calls.
  - `base_url` overrides the default cloud endpoint.
  - `extra_params` is an open-ended key/value bag stored on the client for future metadata use without breaking changes (simply accept and retain it; no mandated behavior yet).

- **Configuration precedence** (must be explicit in every SDK):
  1. Explicit constructor arguments
  2. Environment variables (`RUNAGENT_API_KEY`, `RUNAGENT_BASE_URL`, etc.)
  3. Library defaults (`https://backend.run-agent.ai`, standard port 8450 for local)

### Local Agent Discovery (Optional)
- When `local=true` **and** filesystem access is available, read the SQLite DB at `~/.runagent/runagent_local.db`; reuse the Python schema (`agents` table mapping `agent_id → host, port, framework, status`).  
  ```35:55:runagent/client/client.py
        if local:
            if host and port:
                agent_host = host
                agent_port = port
            else:
                agent_info = self.sdk.db_service.get_agent(agent_id)
                ...
                agent_host = self.agent_info["host"]
                agent_port = self.agent_info["port"]
  ```
- If the agent is missing, raise a clear error telling users to start or register the agent locally.
- SDKs running in sandboxes (browser, mobile, serverless) should skip DB probing and require `host`/`port`.

### Remote Agent Defaults
- Default REST base URL: `https://backend.run-agent.ai` (append `/api/v1`).
- Default WebSocket base: convert to `wss://backend.run-agent.ai/api/v1`.
- Allow overrides via constructor or `RUNAGENT_BASE_URL` env var.
- Respect per-request overrides for self-hosted or staging deployments.

### Architecture Metadata Contract
- Treat `/api/v1/agents/{id}/architecture` as an envelope `{ success, data, message, error, timestamp, request_id }`. Handle both the new envelope and the legacy payload transparently.
- When `success === false`, raise the backend-provided `code/message` and surface any `suggestion`/`details` so users know how to recover (e.g. `AGENT_NOT_FOUND_REMOTE`, `AUTHENTICATION_ERROR`).
- When `success === true`, normalize `data` into a single `AgentArchitecture` structure that includes `agent_id`/`agentId` plus the full entrypoint metadata (`tag`, `file`, `module`, `extractor`, `description`, etc.).
- If `data` or `data.entrypoints` is missing, throw a clear `ARCHITECTURE_MISSING` error instructing users to redeploy or supply proper entrypoints.
- When an entrypoint lookup fails, log or expose the list of entrypoint tags returned by the server to simplify debugging typo/mismatch issues.

### Authentication
- Use Bearer tokens everywhere; reuse the CLI convention (`Authorization: Bearer ${api_key}`) and query-string token fallback for WebSockets.
- Environment variable name: `RUNAGENT_API_KEY`.
- If no API key is present for remote calls, surface a clear error instructing users to set env vars or pass `api_key=`.

### HTTP `run()` Semantics
- Endpoint: `POST /api/v1/agents/{agent_id}/run`.
- Payload:
  ```json
  {
    "entrypoint_tag": "...",
    "input_args": [],
    "input_kwargs": {},
    "timeout_seconds": 300,
    "async_execution": false
  }
  ```
- Deserialize result payloads exactly as the Python client:
  - `data.result_data.data` (legacy structured output)
  - `data` directly when it’s a stringified artifact
- When errors arrive, mirror the Python `RunAgentExecutionError` structure (code/message/suggestion/details).  
  ```70:118:runagent/client/client.py
        response = self.rest_client.run_agent(...)
        if response.get("success"):
            ...
        else:
            error_info = response.get("error")
            ...
            raise RunAgentExecutionError(code=..., message=..., suggestion=..., details=...)
  ```
- Recommended error taxonomy: `AUTHENTICATION_ERROR`, `PERMISSION_ERROR`, `CONNECTION_ERROR`, `VALIDATION_ERROR`, `SERVER_ERROR`, `UNKNOWN_ERROR`.

### WebSocket `run_stream()` Semantics
- Endpoint: `GET wss://.../api/v1/agents/{agent_id}/run-stream`.
- Handshake: immediately send JSON body identical to REST payload (minus `async_execution` optional).
- Incoming frames: JSON objects with `type ∈ {status, data, error}`.
  - `status=stream_started` (informational), `status=stream_completed` (terminate).
  - `data` frames carry `content` (string or JSON); attempt structured deserialization first.
  - `error` frames emit exception and stop the stream.
  ```61:147:runagent/sdk/socket_client.py
        if self.is_local:
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream"
        else:
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream?token={self.api_key}"
        ...
        request_data = { "entrypoint_tag": ..., "input_args": ..., "input_kwargs": ..., "timeout_seconds": 600 }
        websocket.send(json.dumps(request_data))
        for raw_message in websocket:
            message = json.loads(raw_message)
            if message["type"] == "data":
                ...
  ```
- Provide both sync iterator and async iterator variants when idiomatic for the language.

### Extra Params Handling
- Accept `extra_params` at construction; store but do not mutate.
- For now, just keep it accessible via a getter to future-proof metadata features (e.g., tracing context, client tags).

### Error Handling Guidance
- Raise language-idiomatic exceptions derived from a base `RunAgentError`.
- Wrap network-layer issues (timeouts, DNS) into `ConnectionError`.
- When HTTP 401/403 occurs, raise `AuthenticationError` with friendly guidance (e.g., “Set RUNAGENT_API_KEY or pass api_key”).

### Environment And Config Utilities
- Provide helpers to load env vars (`RUNAGENT_API_KEY`, `RUNAGENT_BASE_URL`, optional future keys).
- Offer a `from_env()` factory for ergonomic initialization.
- Document that constructor args override env vars, which override defaults.

### Testing Expectations
- Unit tests: mock REST/WebSocket interactions; assert payload shape and error translation.
- Integration tests: optional “local mode” harness reading a test SQLite DB.
- Provide CI examples for each SDK (reference existing Python/Go/Rust tests under `test_scripts/`).

### Implementation Checklist (Per New SDK)
- [ ] Build `RunAgentClient` with constructor precedence and optional local DB hook.
- [ ] Implement REST `run()` and WebSocket `run_stream()` following payload schemas.
- [ ] Surface consistent error types and messages.
- [ ] Support explicit `api_key`, `base_url`, `host`, `port`.
- [ ] Expose `extra_params` without opinionated behavior.
- [ ] Add environment-based helpers (`from_env`, `configure_from_env`).
- [ ] Include README snippet showing local vs remote usage.
- [ ] Add automated tests for success/error paths.
- [ ] Audit docs to ensure new SDK mirrors this guide.

### Suggested Documentation Template For SDK Repos
1. Quickstart (init client, call `run`, call `run_stream`).
2. Configuration (env vars, constructor precedence).
3. Local vs remote usage (with/without DB, when to set `local=true`).
4. Authentication setup (API key instructions).
5. Error handling reference table.
6. Advanced topics (custom base URL, extra params, retries).
7. Troubleshooting (common connection/auth issues).

### Additional Consistency Requirements
- **Architecture endpoint contract**: every SDK must treat `/api/v1/agents/{id}/architecture` as an envelope `{ success, data, message, error, timestamp, request_id }`, propagate backend `error.code/message/suggestion/details`, normalize the `data` payload (including `agent_id`/`agentId`, `file`, `module`, `extractor`, etc.), and throw a clear `ARCHITECTURE_MISSING` error when `data.entrypoints` is absent.
- **Run vs. runStream guardrails**: enforce that `_stream` tags only work with `runStream()` (`STREAM_ENTRYPOINT` error with a helpful suggestion) and non-stream tags only work with `run()` (`NON_STREAM_ENTRYPOINT` error). This mirrors the CLI and prevents silent misuse.
- **Structured error surfaces**: expose a canonical error type (`RunAgentError`/`RunAgentExecutionError`) that always carries `code`, `message`, `suggestion`, and optional `details`, and reuse the shared code taxonomy (`AUTHENTICATION_ERROR`, `PERMISSION_ERROR`, `VALIDATION_ERROR`, `CONNECTION_ERROR`, `SERVER_ERROR`, `AGENT_NOT_FOUND_LOCAL`, `AGENT_NOT_FOUND_REMOTE`, `STREAM_ENTRYPOINT`, `NON_STREAM_ENTRYPOINT`, `ARCHITECTURE_MISSING`, etc.).
- **Diagnostics for entrypoint mismatches**: when the requested entrypoint isn’t found, log or otherwise expose the set of tags returned by the backend so developers can quickly spot typos or missing deployments.
- **Repository hygiene**: every SDK repo must ship a `README` (installation, configuration, local vs. remote, run vs. runStream examples) and a `PUBLISH.md` (version bump instructions, build/test checklist, npm publish guidance). This keeps packaging and documentation consistent across languages.

### References
```24:37:runagent/constants.py
LOCAL_CACHE_DIRECTORY_PATH = "~/.runagent"
...
DATABASE_FILE_NAME = "runagent_local.db"
```

```25:118:runagent/client/client.py
class RunAgentClient:
    def __init__(..., local: bool = True, host: str = None, port: int = None):
        ...
```

```61:147:runagent/sdk/socket_client.py
        if self.is_local:
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream"
        else:
            uri = f"{self.base_socket_url}/agents/{agent_id}/run-stream?token={self.api_key}"
        ...
```

---
