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
@click.option("--port", type=int, help="Preferred port (auto-allocated if unavailable)")
@click.option("--host", default="127.0.0.1", help="Host to bind server to")
@click.option("--debug", is_flag=True, help="Run server in debug mode")
@click.option("--reload", is_flag=True, help="Enable auto-reload on code changes (development mode)")
@click.option("--no-animation", is_flag=True, help="Skip startup animation")
@click.option("--animation-style",
              type=click.Choice(["field", "ascii", "minimal", "quick"]),
              default="field",
              help="Animation style")
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
def serve(port, host, debug, reload, no_animation, animation_style, path):
    """Start local FastAPI server"""

    try:
        from runagent.cli.branding import print_header, show_simple_serve_progress
        print_header("Serve Agent Locally")
        
        # Show subtle progress animation (unless disabled)
        if not no_animation:
            show_simple_serve_progress("Initializing server")
        
        console.print("[bold]Starting local server with auto port allocation...[/bold]")
        
        # Show progress while creating server
        if not no_animation:
            show_simple_serve_progress("Creating server instance")
        
        # Use the existing LocalServer.from_path method
        server = LocalServer.from_path(path, port=port, host=host)
        
        # Common server startup code
        allocated_host = server.host
        allocated_port = server.port
        
        # Show server info
        console.print(f"\nURL: [bold blue]http://{allocated_host}:{allocated_port}[/bold blue]")
        console.print(f"Docs: [link]http://{allocated_host}:{allocated_port}/docs[/link]")

        try:
                        
            sync_service = get_middleware_sync()
            sync_enabled = sync_service.is_sync_enabled()
            api_key_set = bool(Config.get_api_key())
            
            console.print(f"\n[bold]Middleware Sync Status:[/bold]")
            if sync_enabled:
                console.print(f"   Status: [green]✅ ENABLED[/green]")
                console.print(f"   Local invocations will sync to middleware")
                
                # Test connection
                try:
                    test_result = sync_service.test_connection()
                    if test_result.get("success"):
                        console.print(f"   Connection: [green]✅ Connected to middleware[/green]")
                    else:
                        console.print(f"   Connection: [red]❌ Failed to connect: {test_result.get('error', 'Unknown error')}[/red]")
                except Exception as e:
                    if os.getenv('DISABLE_TRY_CATCH'):
                        raise
                    console.print(f"   Connection: [red]❌ Connection test failed: {e}[/red]")
            else:
                console.print(f"   Status: [yellow]DISABLED[/yellow]")
                if not api_key_set:
                    console.print(f"   Reason: [yellow]API key not configured[/yellow]")
                    console.print(f"   Setup: [cyan]runagent setup --api-key <key>[/cyan]")
                else:
                    user_disabled = not Config.get_user_config().get("local_sync_enabled", True)
                    if user_disabled:
                        console.print(f"   Reason: [yellow]Disabled by user[/yellow]")
                        console.print(f"   Enable: [cyan]runagent local-sync --enable[/cyan]")
                console.print(f"   Local invocations will only be stored locally")
                
        except Exception as e:
            console.print(f"[dim]Note: Could not check middleware sync status: {e}[/dim]")

        # Start server (this will block)
        server.start(debug=debug, reload=reload)

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Server error:[/red] {e}")
        raise click.ClickException("Server failed to start")
