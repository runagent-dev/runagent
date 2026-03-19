"""
CLI commands for agent registration and management.
"""
import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel

from runagent.cli.branding import print_header
from runagent.utils.agent import get_agent_config, get_agent_config_with_defaults
from runagent.utils.agent_id import generate_config_fingerprint, generate_agent_id
from runagent.constants import TEMPLATE_PREPATH, LOCAL_CACHE_DIRECTORY

console = Console()


def _register_agent_core(agent_path: Path | str):
    """
    Core logic for registering an agent (can be called directly or via Click command).
    
    This function is useful when:
    - You manually modified the agent_id in runagent.config.json
    - The agent_id in config doesn't exist in the database
    - You want to register an agent that was created outside of runagent init
    """
    try:
        print_header("Register Agent")
        
        # Resolve path (accept str from e.g. config --register-agent)
        agent_path = Path(agent_path).resolve()
        
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
        from runagent.sdk.db import DBService
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


def _resolve_template_path_for_registration(template_path: str) -> Tuple[Path, Optional[Path]]:
    """
    Resolve template path for registration - supports template shortcuts.
    Returns (resolved_path, temp_dir_for_cleanup).
    """
    path = Path(template_path)
    
    # If path exists, use it directly
    if path.exists():
        return path.resolve(), None
    
    # Check if it looks like a template shortcut (framework/template format)
    parts = template_path.split("/")
    if len(parts) == 2 and "/" in template_path:
        framework, template = parts
        
        # Check local templates first
        possible_paths = [
            Path.cwd() / TEMPLATE_PREPATH / framework / template,
            Path.cwd() / "templates" / framework / template,
        ]
        
        # Also check relative to runagent package if it's installed
        try:
            import runagent
            runagent_package_dir = Path(runagent.__file__).parent.parent
            possible_paths.extend([
                runagent_package_dir / TEMPLATE_PREPATH / framework / template,
                runagent_package_dir / "templates" / framework / template,
            ])
        except (ImportError, AttributeError):
            pass
        
        for local_template_path in possible_paths:
            if local_template_path.exists():
                return local_template_path.resolve(), None
        
        # If not found locally, try to download (but for registration, we prefer local)
        raise click.ClickException(
            f"Template '{template_path}' not found locally. "
            f"Templates must exist locally for registration."
        )
    
    # Path doesn't exist and doesn't look like a template
    raise click.ClickException(
        f"Path not found: {path}\n"
        f"Use a local path or template shortcut like 'openclaw/gateway'"
    )


def _register_template_agent(template_shortcut: str):
    """
    Register a template agent from a shortcut (e.g., 'openclaw/gateway').
    This is a new feature that:
    1. Resolves the template shortcut to a local template
    2. Checks if template is already registered
    3. If not, generates UUID, saves it to a persistent registered templates location
    4. Registers the agent with that UUID
    """
    try:
        print_header("Register Template Agent")
        
        # Resolve template path
        try:
            resolved_path, _ = _resolve_template_path_for_registration(template_shortcut)
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(f"Failed to resolve template '{template_shortcut}': {e}")
        
        console.print(f"[dim]Template: [cyan]{template_shortcut}[/cyan][/dim]")
        console.print(f"[dim]Path: [cyan]{resolved_path}[/cyan][/dim]")
        
        # Load template config
        config_path = resolved_path / "runagent.config.json"
        if not config_path.exists():
            raise click.ClickException(f"No runagent.config.json found in template: {resolved_path}")
        
        agent_config = get_agent_config(resolved_path)
        if not agent_config:
            raise click.ClickException("Failed to load template configuration")
        
        template_name = agent_config.get('template') if isinstance(agent_config, dict) else getattr(agent_config, 'template', None)
        agent_name = agent_config.get('agent_name') if isinstance(agent_config, dict) else getattr(agent_config, 'agent_name', None)
        
        # Check if this template is already registered
        from runagent.sdk.db import DBService, Agent
        from sqlalchemy import or_
        db_service = DBService()
        
        with db_service.db_manager.get_session() as session:
            query = session.query(Agent)
            conditions = []
            if template_name:
                conditions.append(Agent.template == template_name)
            if agent_name:
                conditions.append(Agent.agent_name == agent_name)
            
            existing_agents = []
            if conditions:
                query = query.filter(or_(*conditions))
                existing_agents = query.all()
        
        # If already registered, show existing agent info
        if existing_agents:
            console.print(f"\n[yellow]⚠ Template '{template_shortcut}' is already registered[/yellow]")
            for existing in existing_agents:
                console.print(f"   • Agent ID: [cyan]{existing.agent_id}[/cyan]")
                console.print(f"     Status: [cyan]{existing.status or 'unknown'}[/cyan]")
                console.print(f"     Name: [cyan]{existing.agent_name or 'N/A'}[/cyan]")
            
            from rich.prompt import Confirm
            if not Confirm.ask("\n[bold]Register a new instance anyway?[/bold]", default=False):
                console.print("[dim]Registration cancelled. Use existing agent ID for deployment.[/dim]")
                return
        
        # Create a persistent registered templates directory
        registered_templates_dir = Path(LOCAL_CACHE_DIRECTORY) / "registered_templates"
        registered_templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a working copy for this registered template
        template_working_dir = registered_templates_dir / template_shortcut.replace("/", "_")
        if template_working_dir.exists():
            shutil.rmtree(template_working_dir)
        shutil.copytree(resolved_path, template_working_dir)
        
        # Generate UUID and update config
        new_agent_id = generate_agent_id()
        working_config_path = template_working_dir / "runagent.config.json"
        with working_config_path.open('r') as f:
            config_data = json.load(f)
        config_data['agent_id'] = new_agent_id
        with working_config_path.open('w') as f:
            json.dump(config_data, f, indent=2)
        
        console.print(f"\n[green]✓[/green] Generated agent ID: [cyan]{new_agent_id}[/cyan]")
        console.print(f"[dim]Registered template stored at: [cyan]{template_working_dir}[/cyan][/dim]")
        
        # Register the agent
        config_with_defaults = get_agent_config_with_defaults(template_working_dir)
        config_fingerprint = generate_config_fingerprint(template_working_dir)
        active_project_id = db_service.get_active_project_id()
        
        result = db_service.add_agent(
            agent_id=new_agent_id,
            agent_path=str(template_working_dir),
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
        
        if not result.get('success'):
            raise click.ClickException(f"Failed to register agent: {result.get('error')}")
        
        # Show success message
        console.print(Panel(
            f"[bold green]✅ Template Registered Successfully![/bold green]\n\n"
            f"[dim]Template:[/dim] [cyan]{template_shortcut}[/cyan]\n"
            f"[dim]Agent ID:[/dim] [cyan]{new_agent_id}[/cyan]\n"
            f"[dim]Name:[/dim] [white]{config_with_defaults.get('agent_name', 'Unknown')}[/white]\n"
            f"[dim]Framework:[/dim] [blue]{agent_config.framework}[/blue]\n"
            f"[dim]Status:[/dim] [green]initialized[/green]",
            title="[bold green]Registration Success[/bold green]",
            border_style="green"
        ))
        
        console.print("\n[bold]Next Step:[/bold]")
        console.print(f"   Deploy: [cyan]runagent deploy {template_shortcut}[/cyan]")
        console.print(f"   (This will use agent ID: [cyan]{new_agent_id}[/cyan])")
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Registration error:[/red] {e}")
        raise click.ClickException("Template registration failed")


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
