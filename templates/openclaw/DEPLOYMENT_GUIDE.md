# OpenClaw Deployment Guide

## Overview: Two Templates, One System

OpenClaw has **two components** that work together:

1. **Gateway** (`gateway/`) - The core OpenClaw server (Node.js)
2. **MCP** (`mcp/`) - MCP interface server (Python) that connects to Gateway

You need **BOTH** for a complete OpenClaw deployment.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
│  (Cursor, SDK, REST API, etc.)                          │
└────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              OpenClaw MCP Agent (VM)                    │
│  • Runs: openclaw-mcp server                            │
│  • Exposes: MCP tools (send_message, agent_run, etc.)  │
│  • Connects to: Gateway via WebSocket                  │
└────────────────────┬────────────────────────────────────┘
                      │ WebSocket (ws://gateway_ip:18789)
                      ▼
┌─────────────────────────────────────────────────────────┐
│            OpenClaw Gateway Agent (VM)                  │
│  • Runs: openclaw gateway run                           │
│  • Manages: WhatsApp, Telegram, Skills, Agents         │
│  • Stores: All data in .openclaw (persisted)            │
└─────────────────────────────────────────────────────────┘
```

---

## Deployment Order

### Step 1: Deploy Gateway (Required First)

**Why first?** The MCP needs the Gateway's WebSocket URL to connect.

```bash
# Deploy gateway template
runagent deploy openclaw/gateway

# Or with SDK
from runagent import RunAgentSDK
sdk = RunAgentSDK()
gateway_result = sdk.deploy_remote(
    folder="templates/openclaw/gateway",
    persistent_memory=True,  # CRITICAL for OpenClaw
    user_id="your-user-id"
)

gateway_deployment_id = gateway_result["deployment_id"]
```

**What happens:**
- Creates Gateway VM (Node.js runtime)
- Starts `openclaw gateway run` on port 18789
- Gets VM IP (e.g., `192.168.100.5`)
- Gateway URL: `ws://192.168.100.5:18789`

**Important:** 
- ✅ **MUST** use `persistent_memory=True` (WhatsApp sessions need persistence)
- ✅ Gateway stores everything in `.openclaw` folder (persisted)

---

### Step 2: Deploy MCP (After Gateway)

**Why second?** MCP needs the Gateway URL to connect.

```bash
# Deploy MCP template
runagent deploy openclaw/mcp

# Or with SDK (you need to set gateway URL manually)
from runagent import RunAgentSDK
sdk = RunAgentSDK()

# First, get gateway VM IP from gateway deployment
gateway_vm_ip = "192.168.100.5"  # Get from gateway deployment

# Deploy MCP with gateway URL
mcp_result = sdk.deploy_remote(
    folder="templates/openclaw/mcp",
    config={
        "env_vars": {
            "OPENCLAW_GATEWAY_URL": f"ws://{gateway_vm_ip}:18789",
            "OPENCLAW_GATEWAY_TOKEN": ""  # If gateway uses token auth
        }
    }
)
```

**What happens:**
- Creates MCP VM (Python runtime)
- Installs `openclaw-mcp` package
- Starts `openclaw-mcp` server
- Connects to Gateway via `OPENCLAW_GATEWAY_URL`

**Note:** Currently, you need to manually set `OPENCLAW_GATEWAY_URL`. The planned `POST /openclaw/deploy` endpoint would automate this.

---

## Quick Start: Deploy Both

### Option A: Manual Deployment (Current)

```bash
# 1. Deploy Gateway
runagent deploy openclaw/gateway --persistent-memory

# 2. Get Gateway VM IP from deployment result
# 3. Deploy MCP with gateway URL
runagent deploy openclaw/mcp
# Then update MCP agent env vars with gateway URL via middleware API
```

### Option B: SDK Deployment (Recommended)

```python
from runagent import RunAgentSDK

sdk = RunAgentSDK()

# 1. Deploy Gateway
gateway_result = sdk.deploy_remote(
    folder="templates/openclaw/gateway",
    persistent_memory=True,
    user_id="your-user-id"
)
gateway_deployment_id = gateway_result["deployment_id"]

# 2. Get Gateway VM IP (from deployment metadata or middleware API)
# TODO: Add helper: gateway_ip = sdk.get_gateway_vm_ip(gateway_deployment_id)
gateway_ip = "192.168.100.5"  # Get from deployment

# 3. Deploy MCP with Gateway URL
mcp_result = sdk.deploy_remote(
    folder="templates/openclaw/mcp",
    config={
        "env_vars": {
            "OPENCLAW_GATEWAY_URL": f"ws://{gateway_ip}:18789"
        }
    }
)
mcp_deployment_id = mcp_result["deployment_id"]
```

### Option C: Future - Single Deploy (Not Yet Implemented)

```python
# This will be available when POST /openclaw/deploy is implemented
result = sdk.deploy_openclaw(persistent_memory=True)
# Automatically deploys gateway + MCP and wires them together
```

---

## Which Template Does What?

### `gateway/` Template

**Purpose:** Core OpenClaw server

**Runs:**
- `openclaw gateway run` (Node.js process)
- Listens on port 18789
- Manages WhatsApp, Telegram, Discord, etc.
- Runs AI agents and skills

**Stores:**
- WhatsApp session data
- Channel credentials
- Agent workspaces
- Configuration

**Deployment:**
- ✅ **MUST** use persistent storage (`persistent_memory=True`)
- ✅ Runtime: `openclaw-gateway` (Node.js)
- ✅ Needs `.openclaw` folder persisted

**When to deploy:**
- First, before MCP
- Only one gateway per deployment (can have multiple MCPs connecting to same gateway)

---

### `mcp/` Template

**Purpose:** MCP protocol interface to Gateway

**Runs:**
- `openclaw-mcp` (Python package)
- Exposes MCP tools (send_message, agent_run, channels_list, etc.)
- Connects to Gateway via WebSocket

**Stores:**
- Nothing (stateless, connects remotely)

**Deployment:**
- ✅ Runtime: `python` (standard)
- ✅ Needs `OPENCLAW_GATEWAY_URL` environment variable
- ❌ Does NOT need persistent storage

**When to deploy:**
- After Gateway is deployed
- Can deploy multiple MCPs (for different clients/users)

---

## Usage After Deployment

### Via MCP (Cursor/Claude Desktop)

1. Configure `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "openclaw": {
      "url": "wss://api.runagent.xyz/mcp/{mcp_deployment_id}"
    }
  }
}
```

2. Use in Cursor chat:
   - "Send a WhatsApp message to +1234567890 saying Hello"
   - "List my OpenClaw channels"
   - "Run the agent: summarize my PRs"

### Via REST API

```python
# Use middleware REST API
import requests

# Send message
requests.post(
    f"https://api.runagent.xyz/api/v1/openclaw/{gateway_deployment_id}/send-message",
    json={"channel_id": "whatsapp", "message": "Hello"},
    headers={"Authorization": f"Bearer {api_key}"}
)

# List channels
requests.get(
    f"https://api.runagent.xyz/api/v1/openclaw/{gateway_deployment_id}/channels/list",
    headers={"Authorization": f"Bearer {api_key}"}
)
```

### Via SDK (Future)

```python
# When sdk.openclaw() is implemented
openclaw = sdk.openclaw(gateway_deployment_id)
openclaw.send_message(target="+1234567890", message="Hello", channel="whatsapp")
openclaw.agent_run(message="What's the weather?")
```

---

## Summary

| Template | Deploy Order | Purpose | Runtime | Persistent Storage |
|----------|--------------|---------|---------|-------------------|
| **gateway/** | 1st | Core OpenClaw server | Node.js | ✅ Required |
| **mcp/** | 2nd | MCP interface | Python | ❌ Not needed |

**Deploy both** for a complete OpenClaw setup. Gateway first, then MCP.
