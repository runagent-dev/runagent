"""
CLI command to stop a stateful gateway agent (openclaw / picoclaw / zeroclaw).
"""
import os
import sys

import click
from rich.console import Console

from runagent import RunAgentSDK

console = Console()


@click.command()
@click.argument("agent_id", type=str)
def stop(agent_id: str):
    """
    Stop a stateful gateway agent (openclaw / picoclaw / zeroclaw).

    Flushes all writes to persistent storage first, then destroys the VM.
    Your data (~/.openclaw, ~/.picoclaw, ~/.zeroclaw) is preserved.

    Use 'runagent resume <agent_id>' to restart with storage intact.

    NOTE: This is only for stateful agents. Serverless agents are
    destroyed automatically after execution.
    """
    try:
        sdk = RunAgentSDK()

        if not sdk.is_configured():
            console.print(
                "[red]Not authenticated.[/red] Run [cyan]'runagent setup'[/cyan] first."
            )
            sys.exit(1)

        console.print(f"Stopping agent [bold magenta]{agent_id}[/bold magenta]...")
        console.print("[dim]Syncing persistent storage before shutdown...[/dim]")

        result = sdk.remote.client.stop_agent(agent_id)

        if result.get("success"):
            console.print(f"\n[green]✓[/green] Agent stopped. Persistent storage preserved.")
            console.print(
                f"[dim]Resume with: [cyan]runagent resume {agent_id}[/cyan][/dim]"
            )
        else:
            msg = result.get("message") or "Unknown error"
            # Try to extract message from nested data
            if isinstance(result.get("data"), dict):
                msg = result["data"].get("message", msg)
            console.print(f"\n[red]✗[/red] Stop failed: {msg}")
            sys.exit(1)

    except Exception as e:
        if os.getenv("DISABLE_TRY_CATCH"):
            raise
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)
