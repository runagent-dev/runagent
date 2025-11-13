# RunAgent TypeScript SDK

The RunAgent TypeScript SDK delivers the same `RunAgentClient` interface found in the Python SDK, tailored for both Node.js services and browser-based applications. Use it to invoke agents you deploy with the RunAgent CLI, whether they run locally on the same machine or remotely on `backend.run-agent.ai`.

---

## Installation

```bash
npm install runagent
```

Optional peer dependencies:

- `ws` – required for WebSocket streaming in Node.js environments.
- `better-sqlite3` – only needed when you want Node.js clients to auto-discover local agents via the RunAgent registry. Browser builds should not install it.

```bash
# For Node.js apps that rely on registry discovery:
npm install ws better-sqlite3
```

---

## Configuration Overview

```ts
interface RunAgentConfig {
  agentId: string;
  entrypointTag: string;
  local?: boolean;            // default: false in browser, true in Node if not specified
  host?: string;              // required in browser when local = true (no registry access)
  port?: number;              // required in browser when local = true (no registry access)
  apiKey?: string;            // defaults to RUNAGENT_API_KEY env variable
  baseUrl?: string;           // defaults to RUNAGENT_BASE_URL env variable or https://backend.run-agent.ai
  baseSocketUrl?: string;     // optional override for WebSocket origin
  apiPrefix?: string;         // defaults to /api/v1
  timeoutSeconds?: number;    // defaults to 300
  extraParams?: Record<string, unknown>; // reserved for metadata forwarding
  enableRegistry?: boolean;   // defaults to true in Node, false in browsers
}
```

**Environment variables**

- `RUNAGENT_API_KEY` – API key for remote agents (Bearer token).
- `RUNAGENT_BASE_URL` – override the default remote base URL (useful for staging/self-hosted deployments).

For browser builds, you can expose these via bundler secrets or a custom `globalThis.RUNAGENT_ENV` object before initialising the client.

---

## Usage (Node.js)

### 1. Remote agent

```ts
import { RunAgentClient, RunAgentExecutionError } from 'runagent';

const client = new RunAgentClient({
  agentId: 'agent-id-from-dashboard',
  entrypointTag: 'support_flow',
  apiKey: process.env.RUNAGENT_API_KEY,
  // Optional: baseUrl defaults to https://backend.run-agent.ai
});

await client.initialize();

const result = await client.run({
  customer_email: 'alex@example.com',
  issue_summary: 'Billing question',
});

console.log(result);
```

### 2. Remote streaming

```ts
import { RunAgentClient, RunAgentExecutionError } from 'runagent';

const client = new RunAgentClient({
  agentId: 'agent-id-from-dashboard',
  entrypointTag: 'support_flow_stream',
  apiKey: process.env.RUNAGENT_API_KEY,
});

await client.initialize();

for await (const chunk of client.runStream({ transcript: [] })) {
  console.log('>>>', chunk);
}
```

### 3. Local agent discovery (Node only)

```ts
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: 'local-agent-id',
  entrypointTag: 'minimal',
  local: true,
  // enableRegistry defaults to true in Node; make sure better-sqlite3 is installed
});

await client.initialize(); // looks up ~/.runagent/runagent_local.db
const result = await client.run({ message: 'Hello there' });
console.log(result);
```

If you prefer to bypass the registry (or if `better-sqlite3` isn’t installed), pass the host and port explicitly:

```ts
const client = new RunAgentClient({
  agentId: 'local-agent-id',
  entrypointTag: 'minimal',
  local: true,
  enableRegistry: false,
  host: '127.0.0.1',
  port: 8450,
});
```

---

## Usage (Browser / Edge Runtimes)

Browser builds cannot access the local registry or the filesystem. Provide connection details explicitly and set `enableRegistry: false`.

```ts
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: 'agent-id-from-dashboard',
  entrypointTag: 'support_flow',
  local: false,
  apiKey: window.RUNAGENT_API_KEY, // inject securely via bundler/runtime
  enableRegistry: false,
});

await client.initialize();
const result = await client.run({ message: 'Hello!' });
```

For browser streaming:

```ts
const client = new RunAgentClient({
  agentId: 'agent-id',
  entrypointTag: 'support_flow_stream',
  apiKey: window.RUNAGENT_API_KEY,
  enableRegistry: false,
});

await client.initialize();

for await (const chunk of client.runStream({ message: 'Need help' })) {
  renderChunk(chunk);
}
```

> **Tip:** To keep bundles light, Webpack/Vite can tree-shake the optional registry path when `enableRegistry` is `false`. This avoids shipping Node-only dependencies to the browser.

---

## API Reference

### `RunAgentClient` methods

- `initialize(): Promise<RunAgentClient>`  
  Resolves connection details (registry lookup for local Node use, base URLs for remote) and validates that the requested entrypoint exists.

- `run(inputKwargs?: Record<string, unknown>): Promise<unknown>`  
  Executes a non-streaming entrypoint via HTTPS and returns deserialized output (matching the Python SDK semantics).

- `runStream(inputKwargs?: Record<string, unknown>): AsyncGenerator<unknown>`  
  Streams chunks via WebSocket for entrypoints whose tags end with `_stream`. Throws if you call it on a non-stream entrypoint.

- `getExtraParams(): Record<string, unknown> | undefined`  
  Returns any metadata passed in `extraParams`. Reserved for forward compatibility.

- **Errors**  
  Both `run()` and `runStream()` throw `RunAgentExecutionError` when the agent reports a failure (or when the transport breaks). Inspect `error.code`, `error.message`, and `error.suggestion` to deliver actionable feedback:

  ```ts
  try {
    const result = await client.run({ prompt: '...' });
  } catch (error) {
    if (error instanceof RunAgentExecutionError) {
      console.error(error.code, error.message, error.suggestion);
    } else {
      throw error;
    }
  }
  ```

### Constructor precedence rules

1. Explicit constructor values.
2. Environment variables (`RUNAGENT_API_KEY`, `RUNAGENT_BASE_URL`).
3. Defaults (remote base URL, 300 second timeout, registry disabled in browsers).

---

## Security Best Practices

- Never commit API keys to source control. Use environment variables or secret managers, even on the client side (e.g., provide short-lived tokens from your backend).
- Browsers cannot safely store long-lived keys. Prefer proxying via your backend or issuing ephemeral tokens per session.
- For Node environments, rely on OS-level key storage or `.env` files owned by your deployment platform.

---

## Troubleshooting

- **`Entrypoint ... is streaming. Use runStream()`**  
  Call `runStream()` for tags ending in `_stream`.

- **`Unable to determine host/port` (local mode)**  
  Install `better-sqlite3` and ensure the agent was started through the CLI (`runagent serve ...`). Otherwise provide `host` and `port` manually.

- **Authentication failures (401/403)**  
  Make sure `RUNAGENT_API_KEY` (or `apiKey` in the constructor) corresponds to an account with access to the agent.

- **WebSocket connection fails in browser**  
  Confirm your environment allows WSS connections to `backend.run-agent.ai` and set `enableRegistry: false`.

---

## Example Build Targets

### Vite (Node backend + browser client)

```ts
// vite.config.ts
export default defineConfig({
  define: {
    'process.env.RUNAGENT_API_KEY': JSON.stringify(process.env.RUNAGENT_API_KEY),
    'process.env.RUNAGENT_BASE_URL': JSON.stringify(process.env.RUNAGENT_BASE_URL),
  },
});
```

### Serverless (Edge Functions, Cloudflare Workers, etc.)

Edge runtimes are closer to browsers: disable the registry and pass host/base URLs explicitly.

```ts
const client = new RunAgentClient({
  agentId: env.AGENT_ID,
  entrypointTag: 'edge_entry',
  apiKey: env.RUNAGENT_API_KEY,
  enableRegistry: false,
});
```

---

## Version Compatibility

- SDK version `0.1.26` aligns with the CLI v1+ REST/WebSocket APIs (`/agents/{id}/run` & `/run-stream` routes).
- Breaking changes are communicated in the main RunAgent changelog; the TypeScript SDK follows semantic versioning.

---

## Need Help?

- Consult the main documentation in `docs/sdk/javascript/`.
- Join the RunAgent community channels or open an issue if you encounter integration problems that aren’t covered here.

