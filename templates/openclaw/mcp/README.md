# OpenClaw MCP Template

This template deploys the **OpenClaw MCP server** - provides an MCP (Model Context Protocol) interface to the OpenClaw Gateway.

> **📖 See [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) for complete deployment instructions and how Gateway + MCP work together.**

> **⚠️ IMPORTANT: Deploy the Gateway template FIRST, then deploy this MCP template.**

## Structure

```
mcp/
  agent.py                 # MCP runner entrypoint
  requirements.txt         # openclaw-mcp package
  runagent.config.json     # RunAgent config
  README.md                # This file
```

## Deployment

### 1. Prerequisites

Ensure the OpenClaw Gateway is deployed first and get its deployment ID.

### 2. Deploy MCP with Gateway URL

The MCP agent needs to connect to the gateway. Set `OPENCLAW_GATEWAY_URL`:

```bash
# Deploy MCP template
runagent deploy openclaw/mcp

# Then update env vars via middleware API with gateway URL
```

**Or programmatically:**

```python
from runagent import RunAgentSDK

sdk = RunAgentSDK()

# Get gateway VM IP from gateway deployment (e.g., 192.168.100.5)
gateway_ip = "192.168.100.5"  # Get from gateway deployment result

# Deploy MCP with gateway URL
result = sdk.deploy_remote(
    folder="templates/openclaw/mcp",
    config={
        "env_vars": {
            "OPENCLAW_GATEWAY_URL": f"ws://{gateway_ip}:18789",
            "OPENCLAW_GATEWAY_TOKEN": ""  # If gateway uses token auth
        }
    }
)
```

**Environment Variables:**
- `OPENCLAW_GATEWAY_URL` - **Required** - WebSocket URL (e.g., `ws://192.168.100.5:18789`)
- `OPENCLAW_GATEWAY_TOKEN` - Optional - Gateway auth token

### 4. Runtime Configuration

- **Runtime**: `python` (standard Python agent)
- **Package**: Uses `openclaw-mcp` package (private, not on PyPI)
- **Transport**: stdio (default) or streamable (HTTP)
- **Long-lived**: VM stays running to keep the MCP server active

## Usage

Once deployed, the MCP server is accessible via:

1. **Cursor** - Configure `.cursor/mcp.json` to connect to the MCP endpoint
2. **Claude Desktop** - Add to MCP server configuration
3. **Other clients** - Use the MCP protocol to interact

## MCP Operations

The MCP server exposes OpenClaw operations as tools:

- `openclaw_send_message` - Send WhatsApp/Telegram/etc. messages
- `openclaw_agent_run` - Run AI agent turn
- `openclaw_channels_list` - List available channels
- `openclaw_gateway_status` - Check gateway health
- And 40+ more tools...

See the [mcp-openclaw README](https://github.com/your-org/mcp-openclaw) for full tool list.

## Connection Flow

```
Client (Cursor) → MCP Server (this agent) → OpenClaw Gateway → WhatsApp/Skills
```

## Notes

- The MCP agent must be able to reach the gateway VM (same network or via proxy)
- Device pairing is automated during deployment
- MCP runs indefinitely to keep the VM alive
