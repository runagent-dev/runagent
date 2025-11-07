"""
CLI commands that use the restructured SDK internally.
"""
import os
import json
import uuid

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from runagent import RunAgent
from runagent.sdk.exceptions import (  # RunAgentError,; ConnectionError
    AuthenticationError,
    TemplateError,
    ValidationError,
)
from runagent.client.client import RunAgentClient
from runagent.sdk.server.local_server import LocalServer
from runagent.utils.agent import detect_framework
from runagent.utils.animation import show_subtle_robotic_runner, show_quick_runner
from runagent.utils.config import Config
from runagent.sdk.deployment.middleware_sync import get_middleware_sync
from runagent.cli.utils import add_framework_options, get_selected_framework
from runagent.utils.enums.framework import Framework
console = Console()


def format_error_message(error_info):
    """Format error information from API responses"""
    if isinstance(error_info, dict) and "message" in error_info:
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code")
        if error_code:
            return f"[{error_code}] {error_message}"
        return error_message
    return str(error_info) if error_info else "Unknown error"


# ============================================================================
# Config Command Group
# ============================================================================


@click.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing agent if it already exists")
@click.argument(
    "path",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        path_type=Path,
    ),
    default=".",
)
def upload(path: Path, overwrite: bool):
    """Upload agent to remote server"""

    try:
        from runagent.cli.branding import print_header
        print_header("Upload Agent")
        
        sdk = RunAgent()
        
        # Check authentication
        if not sdk.is_configured():
            console.print(
                "❌ [red]Not authenticated.[/red] Run [cyan]'runagent setup --api-key <key>'[/cyan] first"
            )
            raise click.ClickException("Authentication required")

        # Validate folder
        if not Path(path).exists():
            raise click.ClickException(f"Folder not found: {path}")

        console.print(f"[bold]Uploading agent...[/bold]")
        console.print(f"Source: [cyan]{path}[/cyan]")

        # Upload agent (framework auto-detected)
        result = sdk.upload_agent(folder=path, overwrite=overwrite)

        if result.get("success"):
            agent_id = result["agent_id"]
            console.print(f"\n✅ [green]Upload successful![/green]")
            console.print(f"Agent ID: [bold magenta]{agent_id}[/bold magenta]")
            console.print(f"\n[bold]Next step:[/bold]")
            console.print(f"[cyan]runagent start --id {agent_id}[/cyan]")
        else:
            error_info = result.get("error")
            console.print(f"❌ [red]Upload failed:[/red] {format_error_message(error_info)}")
            if isinstance(error_info, dict):
                suggestion = error_info.get("suggestion")
                if suggestion:
                    console.print(f"[cyan]Suggestion: {suggestion}[/cyan]")
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
        console.print(f"❌ [red]Upload error:[/red] {e}")
        import sys
        sys.exit(1)

