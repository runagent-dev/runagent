## Picoclaw Gateway Template

This template deploys a **Picoclaw** gateway as a long‑running service on RunAgent Serverless.

- **Framework**: `picoclaw`
- **Template shortcut**: `picoclaw/gateway`
- **CLI shortcut**: `runagent deploy picoclaw`

### What this deployment does

- Starts a microVM based on a picoclaw‑specific image (see `Dockerfile.picoclaw-gateway` in `runagent-serverless`).
- Runs the `picoclaw gateway` process inside the VM.
- Persists all Picoclaw data under:
  - `/root/.picoclaw` inside the VM
  - Backed by the Firecracker data disk via `/persistent/.picoclaw`

### Persistent data

Picoclaw stores configuration and workspace under `~/.picoclaw` by default:

- `~/.picoclaw/config.json` – main configuration file (models, channels, tools, etc.).
- `~/.picoclaw/workspace/` – sessions, memory, cron jobs, skills, and heartbeat docs.

This template declares:

```json
{
  "persistent_folders": [".picoclaw"]
}
```

The serverless image mounts the VM data disk at `/persistent` and symlinks:

```text
/root/.picoclaw -> /persistent/.picoclaw
```

so that all configuration and workspace data survive VM restarts as long as the disk is preserved.

### How to deploy

From a configured `runagent` CLI:

```bash
runagent deploy picoclaw
# or explicitly:
runagent deploy picoclaw/gateway
```

The CLI will:

1. Resolve the `picoclaw` shortcut to this template folder.
2. Register the agent if needed and upload a minimal package containing `runagent.config.json`.
3. Ask the serverless engine to create and start a microVM using the picoclaw gateway image.

### After deployment

Once deployment succeeds you can:

- Configure Picoclaw inside the VM by editing `~/.picoclaw/config.json` (mounted from `/persistent/.picoclaw/config.json`).
- Use Picoclaw channels (Telegram, Discord, WhatsApp, etc.) as documented in the upstream Picoclaw README.
- Rely on Picoclaw’s heartbeat and cron features to run periodic tasks from the workspace.

