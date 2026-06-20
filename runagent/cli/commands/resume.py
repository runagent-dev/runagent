"""
CLI command to resume a stopped stateful gateway agent.
"""
import os
import sys

import click
from rich.console import Console

from runagent import RunAgentSDK

console = Console()


@click.command()
@click.argument("agent_id", type=str)
def resume(agent_id: str):
    """
    Resume a stopped stateful gateway agent.

    Starts a new VM and reattaches persistent storage. Your data
    (~/.openclaw, ~/.picoclaw, ~/.zeroclaw) is exactly as you left it.

    NOTE: Only for stateful agents (openclaw / picoclaw / zeroclaw).
    """
    try:
        sdk = RunAgentSDK()

        if not sdk.is_configured():
            console.print(
                "[red]Not authenticated.[/red] Run [cyan]'runagent setup'[/cyan] first."
            )
            sys.exit(1)

        console.print(f"Resuming agent [bold magenta]{agent_id}[/bold magenta]...")
        console.print("[dim]Starting VM and reattaching persistent storage...[/dim]")

        result = sdk.remote.client.resume_agent(agent_id)

        if result.get("success"):
            data = result.get("data", {})
            console.print(f"\n[green]✓[/green] Agent resumed!")
            if data.get("vm_ip"):
                console.print(f"  VM IP:  [green]{data['vm_ip']}[/green]")
            if data.get("vm_id"):
                console.print(f"  VM ID:  [cyan]{data['vm_id']}[/cyan]")
            console.print("[dim]Persistent storage reattached.[/dim]")
        else:
            msg = result.get("message") or "Unknown error"
            if isinstance(result.get("data"), dict):
                msg = result["data"].get("message", msg)
            console.print(f"\n[red]✗[/red] Resume failed: {msg}")
            sys.exit(1)

    except Exception as e:
        if os.getenv("DISABLE_TRY_CATCH"):
            raise
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)
