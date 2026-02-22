"""
OpenClaw MCP Agent - Runs openclaw-mcp server.

This agent keeps the VM running and exposes the MCP server.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_mcp():
    """
    Start openclaw-mcp server in background.

    Spawns the MCP server process and returns immediately. The process
    runs in background; VM stays alive. The MCP server connects to
    OpenClaw Gateway via OPENCLAW_GATEWAY_URL.
    """
    gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL")
    gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")

    if not gateway_url:
        return {
            "success": False,
            "error": "OPENCLAW_GATEWAY_URL environment variable not set",
            "message": "Set OPENCLAW_GATEWAY_URL to the gateway WebSocket URL (e.g., ws://192.168.100.5:18789)",
        }

    env = os.environ.copy()
    env["OPENCLAW_GATEWAY_URL"] = gateway_url
    if gateway_token:
        env["OPENCLAW_GATEWAY_TOKEN"] = gateway_token

    transport = os.environ.get("OPENCLAW_MCP_TRANSPORT", "streamable")
    port = int(os.environ.get("OPENCLAW_MCP_PORT", "8000"))

    try:
        if transport == "streamable":
            cmd = ["openclaw-mcp", "--transport", "streamable", "--port", str(port)]
        else:
            cmd = ["openclaw-mcp"]

        print(f"Starting openclaw-mcp with gateway: {gateway_url}", file=sys.stderr)
        print(f"Transport: {transport}, port: {port}", file=sys.stderr)

        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            start_new_session=True,
        )

        return {
            "success": True,
            "message": "MCP server started in background",
            "pid": process.pid,
            "port": port if transport == "streamable" else None,
            "gateway_url": gateway_url,
        }

    except FileNotFoundError:
        return {
            "success": False,
            "error": "openclaw-mcp not found",
            "message": "Install openclaw-mcp: pip install openclaw-mcp",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to start openclaw-mcp: {e}",
        }
