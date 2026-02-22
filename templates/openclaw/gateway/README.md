# OpenClaw Gateway Template

This template deploys the **OpenClaw Gateway** - the core OpenClaw server that runs WhatsApp, skills, and AI agents.

> **📖 See [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) for complete deployment instructions and how Gateway + MCP work together.**

## Structure

```
gateway/
  .agent_files/
    .gitkeep                 # Keeps directory in git (openclaw.json auto-created at runtime)
  runagent.config.json       # RunAgent config
  README.md                  # This file
```

## Deployment

### 1. Prepare Configuration

The `.agent_files/` directory will contain:
- `openclaw.json` - OpenClaw configuration (auto-created on first run or copied from example)
- `credentials/` - WhatsApp and other channel credentials (populated during setup)

These are **not** included in the template by default. They will be:
- Created automatically when the gateway starts
- Or uploaded as part of the agent deployment zip

### 2. Deploy with RunAgent

```bash
# From the gateway template directory
runagent deploy .

# Or programmatically
from runagent import RunAgentSDK
sdk = RunAgentSDK()
result = sdk.deploy_remote(folder="templates/openclaw/gateway")
```

### 3. Runtime Configuration

- **Runtime**: `openclaw-gateway` (automatically set via metadata)
- **Port**: Gateway listens on port 18789 inside the VM
- **Network**: VM gets a TAP device with an IP (e.g., 192.168.100.5)
- **Persistent storage**: `.openclaw` directory is persisted to `/persistent/.openclaw`

#### Persistent Storage Details

The template includes `"persistent_folders": [".openclaw"]` in `runagent.config.json`. This tells RunAgent to:

1. **Mount persistent disk** (`/dev/vdb`) to `/persistent` when the VM starts
2. **Create symlink** `/root/.openclaw` → `/persistent/.openclaw`
3. **Persist data** across VM restarts (WhatsApp sessions, config, credentials, etc.)

**Important**: When deploying, ensure `persistent_memory=true` is set (or use the SDK's persistent storage option). Without persistent storage, `.openclaw` data will be lost on VM restart.

The `.openclaw` folder contains:
- `openclaw.json` - Gateway configuration
- `credentials/` - WhatsApp and channel authentication data
- `workspace/` - Agent workspaces and state
- `skills/` - Custom skills
- Other runtime data

### 4. Gateway URL

After deployment, the gateway URL will be:
- Internal: `ws://{vm_ip}:18789`
- Public (via middleware proxy): `wss://api.runagent.xyz/openclaw/{deployment_id}/gateway`

## Usage

The gateway runs automatically when the VM starts. You can interact with it via:

1. **MCP Server** - Connect the MCP agent to this gateway
2. **SDK** - Use `sdk.openclaw(deployment_id).send_message(...)` 
3. **Direct CLI** - Execute commands in the VM: `openclaw channels list`

## Notes

- The gateway needs persistent storage for WhatsApp sessions and configuration
- Credentials must be provided during deployment or will be created on first run
- Auto-pairing will be handled by the middleware for MCP connections

## Persistent Storage

For detailed information about how persistent storage works for OpenClaw, see [PERSISTENT_STORAGE.md](../PERSISTENT_STORAGE.md).
