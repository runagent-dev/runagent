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
@click.option("--id", "agent_id", required=True, help="Agent ID to delete")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def delete(agent_id, yes):
    """Delete an agent from the local database"""
    try:
        from runagent.cli.branding import print_header
        print_header("Delete Agent")
        
        sdk = RunAgent()
        
        # Get agent info first
        agent = sdk.db_service.get_agent(agent_id)
        if not agent:
            console.print(f"❌ [red]Agent {agent_id} not found in database[/red]")
            
            # Show available agents
            console.print("\n[cyan]Available agents:[/cyan]")
            agents = sdk.db_service.list_agents()
            if agents:
                table = Table(title="Available Agents")
                table.add_column("Agent ID", style="magenta")
                table.add_column("Framework", style="green")
                table.add_column("Status", style="yellow")
                table.add_column("Deployed At", style="dim")
                
                for agent in agents[:10]:  # Show first 10
                    table.add_row(
                        agent['agent_id'][:8] + "...",
                        agent['framework'],
                        agent['status'],
                        agent['deployed_at'] or "Unknown"
                    )
                console.print(table)
            else:
                console.print("   No agents found in database")
            
            raise click.ClickException("Agent not found")
        
        # Show agent details
        console.print(f"\n[yellow]Agent to be deleted:[/yellow]")
        console.print(f"   Agent ID: [bold magenta]{agent['agent_id']}[/bold magenta]")
        console.print(f"   Framework: [green]{agent['framework']}[/green]")
        console.print(f"   Path: [blue]{agent['agent_path']}[/blue]")
        console.print(f"   Status: [yellow]{agent['status']}[/yellow]")
        console.print(f"   Deployed: [dim]{agent['deployed_at']}[/dim]")
        console.print(f"   Total Runs: [cyan]{agent['run_count']}[/cyan]")
        
        # Confirmation
        if not yes:
            if not click.confirm("\n[yellow]This will permanently delete the agent from the database. Continue?[/yellow]"):
                console.print("Deletion cancelled.")
                return
        
        # Delete the agent
        result = sdk.db_service.force_delete_agent(agent_id)
        
        if result["success"]:
            console.print(f"\n✅ [green]Agent {agent_id} deleted successfully![/green]")
        else:
            console.print(f"❌ [red]Failed to delete agent:[/red] {format_error_message(result.get('error'))}")
            import sys
            sys.exit(1)
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Delete error:[/red] {e}")
        import sys
        sys.exit(1)
