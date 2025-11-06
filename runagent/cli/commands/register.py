"""
CLI commands for agent registration and management.
"""
import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from runagent.cli.branding import print_header
from runagent.sdk import RunAgent
from runagent.sdk.db import DBService
from runagent.utils.agent import get_agent_config, get_agent_config_with_defaults
from runagent.utils.agent_id import generate_config_fingerprint

console = Console()


def _register_agent_core(agent_path: Path):
    """
    Core logic for registering an agent (can be called directly or via Click command).
    
    This function is useful when:
    - You manually modified the agent_id in runagent.config.json
    - The agent_id in config doesn't exist in the database
    - You want to register an agent that was created outside of runagent init
    """
    try:
        print_header("Register Agent")
        
        # Resolve path
        agent_path = agent_path.resolve()
        
        # Check if runagent.config.json exists
        config_path = agent_path / "runagent.config.json"
        if not config_path.exists():
            console.print(f"❌ [red]No runagent.config.json found in {agent_path}[/red]")
            console.print("[cyan]Make sure you're in an agent directory or run 'runagent init' first[/cyan]")
            raise click.ClickException("Agent configuration not found")
        
        # Load agent config
        try:
            agent_config = get_agent_config(agent_path)
            if not agent_config:
                console.print(f"❌ [red]Failed to load agent configuration[/red]")
                raise click.ClickException("Invalid agent configuration")
                
            agent_id = agent_config.agent_id
            if not agent_id:
                console.print(f"❌ [red]No agent_id found in configuration[/red]")
                console.print("[cyan]Run 'runagent init' to create a proper agent configuration[/cyan]")
                raise click.ClickException("Missing agent_id in configuration")
                
        except Exception as e:
            console.print(f"❌ [red]Error loading agent config: {e}[/red]")
            raise click.ClickException("Failed to load agent configuration")
        
        # Check if agent already exists
        db_service = DBService()
        existing_agent = db_service.get_agent(agent_id)
        
        if existing_agent:
            console.print(f"[yellow]Agent {agent_id} already exists in database[/yellow]")
            console.print(f"[cyan]Current status: {existing_agent.get('status', 'unknown')}[/cyan]")
            console.print(f"[cyan]Remote status: {existing_agent.get('remote_status', 'unknown')}[/cyan]")
            
            from rich.prompt import Confirm
            overwrite = Confirm.ask("Do you want to update the existing agent?", default=False)
            
            if not overwrite:
                console.print("❌ [red]Registration cancelled[/red]")
                return
        
        # Get agent details
        config_with_defaults = get_agent_config_with_defaults(agent_path)
        config_fingerprint = generate_config_fingerprint(agent_path)
        
        # Get active project ID from user metadata
        active_project_id = db_service.get_active_project_id()
        
        # Register/update agent
        if existing_agent:
            # Update existing agent
            result = db_service.update_agent(
                agent_id=agent_id,
                agent_path=str(agent_path),
                framework=agent_config.framework.value if hasattr(agent_config.framework, 'value') else str(agent_config.framework),
                status="initialized",  # Reset to initialized
                remote_status="initialized",  # Reset to initialized
                fingerprint=config_fingerprint,
                agent_name=config_with_defaults.get('agent_name'),
                description=config_with_defaults.get('description'),
                template=config_with_defaults.get('template'),
                version=config_with_defaults.get('version'),
                initialized_at=config_with_defaults.get('created_at'),
                config_fingerprint=config_fingerprint,
                project_id=active_project_id,
            )
            
            if result.get('success'):
                console.print(f"✅ [green]Agent {agent_id} updated successfully[/green]")
            else:
                console.print(f"❌ [red]Failed to update agent: {result.get('error')}[/red]")
                raise click.ClickException("Agent update failed")
        else:
            # Add new agent
            result = db_service.add_agent(
                agent_id=agent_id,
                agent_path=str(agent_path),
                host="localhost",
                port=8000,
                framework=agent_config.framework.value if hasattr(agent_config.framework, 'value') else str(agent_config.framework),
                status="initialized",
                agent_name=config_with_defaults.get('agent_name'),
                description=config_with_defaults.get('description'),
                template=config_with_defaults.get('template'),
                version=config_with_defaults.get('version'),
                initialized_at=config_with_defaults.get('created_at'),
                config_fingerprint=config_fingerprint,
                project_id=active_project_id,
            )
            
            if result.get('success'):
                console.print(f"✅ [green]Agent {agent_id} registered successfully[/green]")
            else:
                console.print(f"❌ [red]Failed to register agent: {result.get('error')}[/red]")
                raise click.ClickException("Agent registration failed")
        
        # Show success message
        console.print(Panel(
            f"[bold green]✅ Agent Registration Complete![/bold green]\n\n"
            f"[dim]Agent ID:[/dim] [cyan]{agent_id}[/cyan]\n"
            f"[dim]Name:[/dim] [white]{config_with_defaults.get('agent_name', 'Unknown')}[/white]\n"
            f"[dim]Framework:[/dim] [blue]{agent_config.framework}[/blue]\n"
            f"[dim]Status:[/dim] [green]initialized[/green]\n"
            f"[dim]Remote Status:[/dim] [green]initialized[/green]\n"
            f"[dim]Path:[/dim] [blue]{agent_path}[/blue]",
            title="[bold green]Registration Success[/bold green]",
            border_style="green"
        ))
        
        console.print("\n[bold]Next Steps:[/bold]")
        console.print(f"   1. Serve locally: [cyan]runagent serve .[/cyan]")
        console.print(f"   2. Deploy remotely: [cyan]runagent deploy .[/cyan]")
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Registration error:[/red] {e}")
        raise click.ClickException("Agent registration failed")


@click.command()
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
def register(path: Path):
    """Register a modified agent in the database."""
    _register_agent_core(path)
