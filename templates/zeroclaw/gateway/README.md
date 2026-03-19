# zeroclaw/gateway

This template deploys a 24/7 ZeroClaw runtime inside a RunAgent serverless microVM.

## What gets deployed
- A long-lived ZeroClaw service (the microVM keeps running)
- A persistent workspace under:
  - config: `/root/.zeroclaw/config.toml`
  - workspace: `/root/.zeroclaw/workspace`
- Persistent storage is backed by the VM data disk via `/persistent/.zeroclaw`.

## Deploy
From your host:

```bash
runagent deploy zeroclaw/gateway
# or (shortcut)
runagent deploy zeroclaw
```

## After deployment
1. Get the `Agent ID` from the deploy output.
2. Connect/configure using ZeroClaw configuration tools (or via your UI/Nanobot).
3. Ensure channels are bound in ZeroClaw `config.toml` / runtime as required.

## Internal runtime
The serverless engine starts the microVM with a ZeroClaw-specific image that runs:
- `zeroclaw daemon`
- `zeroclaw gateway` (webhook gateway/server)

