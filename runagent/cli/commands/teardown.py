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
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def teardown(yes):
    """Complete teardown - Remove RunAgent configuration AND database"""
    try:
        from runagent.cli.branding import print_header
        from rich.panel import Panel
        from rich.prompt import Confirm
        from runagent.constants import LOCAL_CACHE_DIRECTORY, DATABASE_FILE_NAME
        from pathlib import Path
        
        print_header("Complete Teardown")
        
        sdk = RunAgent()

        if not yes:
            config_status = sdk.get_config_status()
            db_stats = sdk.db_service.get_database_stats()
            
            # Show what will be deleted
            console.print(Panel(
                "[bold red]COMPLETE TEARDOWN[/bold red]\n\n"
                "This will permanently delete:\n"
                "  • All configuration (API key, user info, settings)\n"
                "  • Complete database (all agents, runs, logs, history)\n"
                "  • All local agent data\n\n"
                "[yellow]This action CANNOT be undone![/yellow]",
                title="[bold red]Warning[/bold red]",
                border_style="red"
            ))
            
            console.print("\n[bold]Current data:[/bold]")
            if config_status.get("configured"):
                console.print(f"   User: [cyan]{config_status.get('user_info', {}).get('email', 'N/A')}[/cyan]")
            console.print(f"   Total agents: [yellow]{db_stats.get('total_agents', 0)}[/yellow]")
            console.print(f"   Total runs: [yellow]{db_stats.get('total_runs', 0)}[/yellow]")
            console.print(f"   Database size: [yellow]{db_stats.get('database_size_mb', 0)} MB[/yellow]\n")

            if not Confirm.ask(
                "[bold red]Are you absolutely sure you want to proceed?[/bold red]",
                default=False
            ):
                console.print("[dim]Teardown cancelled.[/dim]")
                return

        # Clear configuration from database
        sdk.config.clear()

        # Close database connections
        sdk.db_service.close()
        
        # Delete database file
        db_path = Path(LOCAL_CACHE_DIRECTORY) / DATABASE_FILE_NAME
        if db_path.exists():
            db_path.unlink()
            console.print(f"[dim]Deleted database: {db_path}[/dim]")
        
        # Delete legacy JSON file if exists
        json_file = Path(LOCAL_CACHE_DIRECTORY) / "user_data.json"
        if json_file.exists():
            json_file.unlink()
            console.print(f"[dim]Deleted legacy config: {json_file}[/dim]")

        console.print(Panel(
            "[bold green]✅ RunAgent teardown completed successfully![/bold green]\n\n"
            "All configuration and data have been removed.\n\n"
            "[dim]To start fresh, run:[/dim] [cyan]runagent setup[/cyan]",
            title="[bold green]Complete[/bold green]",
            border_style="green"
        ))

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(Panel(
            f"[red]❌ Teardown error:[/red] {str(e)}",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))
        raise click.ClickException("Teardown failed")
