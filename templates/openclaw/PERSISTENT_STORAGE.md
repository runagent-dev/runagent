# OpenClaw Persistent Storage in RunAgent

OpenClaw stores all its data (config, credentials, sessions, workspace) in the `.openclaw` folder. In RunAgent cloud, this folder must be persisted across VM restarts.

## How It Works

### 1. Configuration

The gateway template includes `persistent_folders` in `runagent.config.json`:

```json
{
  "persistent_folders": [".openclaw"]
}
```

### 2. Runtime Behavior

When the VM starts with persistent storage enabled:

1. **Persistent disk** (`/dev/vdb`) is mounted to `/persistent`
2. **Symlink created**: `/root/.openclaw` → `/persistent/.openclaw`
3. **Data persists** across VM restarts, snapshots, and deployments

### 3. What Gets Persisted

The `.openclaw` folder contains:

- `openclaw.json` - Gateway configuration
- `credentials/` - WhatsApp, Telegram, Discord, etc. authentication
- `workspace/` - Agent workspaces and conversation state
- `skills/` - Custom skills and their state
- `cron/` - Cron job definitions
- Other runtime data

## Deployment Requirements

**Gateway VM**: **MUST** use persistent storage (`persistent_memory=true`)

Without persistent storage:
- ❌ WhatsApp sessions lost on restart
- ❌ Channel credentials lost
- ❌ Agent workspace state lost
- ❌ Configuration changes lost

**MCP VM**: **NOT required** (connects remotely to Gateway)

The MCP agent connects to Gateway via `OPENCLAW_GATEWAY_URL` and doesn't store local state.

## Example: SDK Deployment with Persistent Storage

```python
from runagent import RunAgentSDK

sdk = RunAgentSDK()

# Deploy gateway with persistent storage
deployment = sdk.deploy_remote(
    folder="templates/openclaw/gateway",
    persistent_memory=True,  # CRITICAL for OpenClaw
    user_id="user-123"       # Required for persistent storage
)

gateway_deployment_id = deployment["deployment_id"]
```

## Verification

After deployment, verify persistent storage is working:

```bash
# Execute command in gateway VM
sdk.execute_command(
    vm_id=gateway_vm_id,
    command="ls -la /root/.openclaw && test -L /root/.openclaw && echo 'Symlink OK' || echo 'No symlink'"
)
```

Expected output:
```
Symlink OK
```

## Troubleshooting

### Persistent storage not mounted

**Symptom**: `/root/.openclaw` is a regular directory, not a symlink

**Fix**: Ensure `persistent_memory=true` and `user_id` are set during deployment

### Data lost after restart

**Symptom**: WhatsApp sessions, credentials, or config disappear

**Fix**: 
1. Check VM has persistent disk: `lsblk` should show `/dev/vdb`
2. Check mount: `mount | grep persistent` should show `/dev/vdb on /persistent`
3. Check symlink: `ls -la /root/.openclaw` should show `-> /persistent/.openclaw`

### Config file not found

**Symptom**: Gateway can't find `openclaw.json`

**Fix**: The config is auto-created on first run. If missing, check:
- Persistent storage is mounted
- Symlink exists: `/root/.openclaw` → `/persistent/.openclaw`
- Permissions: `/persistent/.openclaw` should be writable
