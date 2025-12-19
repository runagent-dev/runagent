"""
CLI commands that use the restructured SDK internally.
"""
import os
import json


import click
from rich.console import Console

from runagent import RunAgent
from runagent.sdk.exceptions import (  # RunAgentError,; ConnectionError
    AuthenticationError,
)
console = Console()


def format_error_message(error_info):
    """Format error information from API responses"""
    if isinstance(error_info, dict) and "message" in error_info:
        # New format with ErrorDetail object
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code", "UNKNOWN_ERROR")
        return f"[{error_code}] {error_message}"
    else:
        # Fallback to old format for backward compatibility
        return str(error_info) if error_info else "Unknown error"


# ============================================================================
# Config Command Group
# ============================================================================

@click.command()
@click.option("--id", "agent_id", required=True, help="Agent ID to start")
@click.option("--config", help="JSON configuration for deployment")
def start(agent_id, config):
    """Start an uploaded agent on remote server"""

    try:
        from runagent.cli.branding import print_header
        print_header("Start Remote Agent")
        
        sdk = RunAgent()

        # Check authentication
        if not sdk.is_configured():
            console.print(
                "❌ [red]Not authenticated.[/red] Run [cyan]'runagent setup --api-key <key>'[/cyan] first"
            )
            raise click.ClickException("Authentication required")

        # Parse config
        config_dict = {}
        if config:
            try:
                config_dict = json.loads(config)
            except json.JSONDecodeError:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                raise click.ClickException("Invalid JSON in config parameter")

        console.print(f"[bold]Starting agent...[/bold]")
        console.print(f"Agent ID: [magenta]{agent_id}[/magenta]")

        # Start agent
        result = sdk.start_remote_agent(agent_id, config_dict)

        if result.get("success"):
            console.print(f"\n✅ [green]Agent started successfully![/green]")
            console.print(f"Endpoint: [link]{result.get('endpoint')}[/link]")
        else:
            console.print(f"❌ [red]Start failed:[/red] {format_error_message(result.get('error'))}")
            import sys
            sys.exit(1)

    except AuthenticationError as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Authentication error:[/red] {e}")
        import sys
        sys.exit(1)
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Start error:[/red] {e}")
        import sys
        sys.exit(1)
