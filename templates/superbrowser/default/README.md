# SuperBrowser (serverless)

Deploy [SuperBrowser](https://github.com/runagent-dev/runagent-superbrowser) — a
stealth Puppeteer engine with captcha/Cloudflare handling — to the RunAgent
serverless platform. Once deployed it runs on **on-demand micro-VMs** with a
**per-user persistent browser session** (cookies/profiles survive across calls),
and is callable from **every** RunAgent SDK.

The heavy Node + Chromium engine is built server-side from the `superbrowser`
runtime image — this project is just the agent manifest + entrypoint, so it's
tiny.

## Deploy

```bash
# 1. Scaffold (or use this directory directly)
runagent init my-browser --from-template superbrowser/default
cd my-browser

# 2. Add your LLM key (required) — see .env.example
cp .env.example .env
$EDITOR .env        # set LLM_MODEL + OPENAI_API_KEY (or ANTHROPIC_API_KEY)

# 3. Deploy — prints your agent_id
runagent deploy .
```

## Use it from any SDK

The deploy prints an `agent_id`. Call the `run` entrypoint from any RunAgent SDK
with `local=false` and `persistent_memory=true` (per-user warm sessions):

```python
# Python (generic runagent SDK)
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="<agent_id>", entrypoint_tag="run",
    local=False, persistent_memory=True,
)
print(client.run(task="find the cheapest 4-star hotel in Sylhet this weekend"))
```

```typescript
// TypeScript (runagent-ts)
import { RunAgentClient } from "runagent";
const client = new RunAgentClient({
  agentId: "<agent_id>", entrypointTag: "run",
  local: false, apiKey: process.env.RUNAGENT_API_KEY,
});
await client.initialize();
console.log(await client.run({ task: "...", mode: "auto" }));
```

The Python `runagent_superbrowser` package also offers a convenience wrapper:
`SuperBrowser(remote=True, persistent=True, agent_id="<agent_id>").run("...")`.

## Entrypoint

`main.py:run(task, mode="auto", url=None, ...)` returns a JSON-serializable
result (`text`, `success`, `data`, `error`, `task_id`, `mode`). `mode` is
`auto` | `fetch` (read-only) | `browser` (interactive).

For progress events, call the `run_stream` entrypoint (`entrypoint_tag="run_stream"`):
it yields `status` / `thinking` / `tool` / `message` events and a final
`{"type": "result", ...}` matching `run`.

## Local development

For local iteration use the SuperBrowser repo directly (`npm run dev` + the
Python SDK in local mode) — see its README. This template is for serverless
deploy only.
