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
from runagent.cli.utils import add_framework_options, get_selected_framework, safe_prompt
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


@click.group(invoke_without_command=True)
@click.option("--set-api-key", help="Set API key directly (e.g., runagent config --set-api-key YOUR_KEY)")
@click.option("--set-base-url", help="Set base URL directly (e.g., runagent config --set-base-url https://api.example.com)")
@click.option("--register-agent", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), help="Register a modified agent in the database")
@click.option("--delete-agent", help="Delete an agent by ID")
@click.pass_context
def config(ctx, set_api_key, set_base_url, register_agent, delete_agent):
    """
    Manage RunAgent configuration
    
    \b
    Interactive mode (for humans):
      $ runagent config
    
    \b
    Direct flags (for scripts/agents):
      $ runagent config --set-api-key YOUR_KEY
      $ runagent config --set-base-url https://api.example.com
      $ runagent config --register-agent .
      $ runagent config --delete-agent <agent_id>
    
    \b
    Subcommands:
      $ runagent config reset
    """
    
    # Handle direct flag options
    if set_api_key:
        _set_api_key_direct(set_api_key)
        return
    
    if set_base_url:
        _set_base_url_direct(set_base_url)
        return
    
    if register_agent:
        from .register import _register_agent_core
        return _register_agent_core(register_agent)
    
    if delete_agent:
        from .delete import delete as delete_func
        return delete_func(delete_agent, False)
    
    # If no subcommand and no flags, show interactive menu
    if ctx.invoked_subcommand is None:
        show_interactive_config_menu()


def _set_api_key_direct(api_key: str):
    """Set API key directly (for --set-api-key flag) with validation"""
    from rich.panel import Panel
    from rich.status import Status
    from runagent.constants import DEFAULT_BASE_URL
    
    if not api_key or not api_key.strip():
        console.print(Panel(
            "[red]❌ API key cannot be empty[/red]",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))
        raise click.ClickException("Invalid API key")
    
    # Validate and fetch user info
    try:
        sdk = RunAgent()
        base_url = Config.get_base_url() or DEFAULT_BASE_URL
        
        with Status("[bold cyan]Validating credentials...", spinner="dots"):
            sdk.configure(api_key=api_key, base_url=base_url, save=True)
        
        # Get user info
        user_config = Config.get_user_config()
        
        # Build success message
        success_msg = (
            "[bold green]✅ API key updated successfully![/bold green]\n\n"
            f"[dim]User:[/dim] [cyan]{user_config.get('user_email', 'N/A')}[/cyan]\n"
            f"[dim]Tier:[/dim] [yellow]{user_config.get('user_tier', 'N/A')}[/yellow]"
        )
        
        # Add project if available
        if user_config.get('active_project_name'):
            success_msg += f"\n[dim]Project:[/dim] [green]{user_config.get('active_project_name')}[/green]"
        
        console.print(Panel(
            success_msg,
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
        
    except AuthenticationError as e:
        console.print(Panel(
            f"[red]❌ Authentication failed[/red]\n\n"
            f"[dim]Error:[/dim] {str(e)}\n\n"
            "[yellow]Please check your API key and try again[/yellow]",
            title="[bold red]Validation Error[/bold red]",
            border_style="red"
        ))
        raise click.ClickException("Authentication failed")
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(Panel(
            f"[red]❌ Failed to save API key[/red]\n\n"
            f"[dim]Error:[/dim] {str(e)}",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))
        raise click.ClickException("Failed to save configuration")


def _set_base_url_direct(base_url: str):
    """Set base URL directly (for --set-base-url flag)"""
    from rich.panel import Panel
    
    # Validate URL format
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    success = Config.set_base_url(base_url)
    
    if success:
        console.print(Panel(
            f"[bold green]✅ Base URL updated successfully![/bold green]\n\n"
            f"[dim]New URL:[/dim] [cyan]{base_url}[/cyan]",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[red]❌ Failed to save base URL[/red]",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))
        raise click.ClickException("Failed to save configuration")


def show_interactive_config_menu():
    """Show interactive configuration menu"""
    try:
        from rich.panel import Panel
        from runagent.cli.branding import print_header
        import inquirer
        
        print_header("Configuration")
        
        questions = [
            inquirer.List(
                'config_option',
                message="What would you like to configure?",
                choices=[
                    ('API Key', 'api_key'),
                    ('Base URL', 'base_url'),
                    ('Active Project', 'project'),
                    ('Sync Settings', 'sync'),
                    ('Reset Configuration', 'reset'),
                ],
                carousel=True
            ),
        ]
        
        answers = safe_prompt(questions, "[dim]Configuration cancelled.[/dim]")
        if not answers:
            return
        
        option = answers['config_option']
        
        # Route to appropriate handler
        if option == 'api_key':
            _interactive_set_api_key()
        elif option == 'base_url':
            _interactive_set_base_url()
        elif option == 'project':
            _interactive_set_project()
        elif option == 'sync':
            _interactive_sync_settings()
        elif option == 'reset':
            _interactive_reset_config()
            
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"[red]Error:[/red] {e}")


def _interactive_set_api_key():
    """Interactive API key setup with validation"""
    from rich.prompt import Prompt
    from rich.panel import Panel
    from rich.status import Status
    from runagent.constants import DEFAULT_BASE_URL
    
    api_key = Prompt.ask("[cyan]Enter your API key[/cyan]", password=True)
    
    if not api_key or not api_key.strip():
        console.print(Panel(
            "[red]❌ API key cannot be empty[/red]",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))
        return
    
    # Validate and fetch user info
    try:
        sdk = RunAgent()
        base_url = Config.get_base_url() or DEFAULT_BASE_URL
        
        with Status("[bold cyan]Validating credentials...", spinner="dots"):
            sdk.configure(api_key=api_key, base_url=base_url, save=True)
        
        # Get user info
        user_config = Config.get_user_config()
        
        # Build success message
        success_msg = (
            "[bold green]✅ API key updated successfully![/bold green]\n\n"
            f"[dim]User:[/dim] [cyan]{user_config.get('user_email', 'N/A')}[/cyan]\n"
            f"[dim]Tier:[/dim] [yellow]{user_config.get('user_tier', 'N/A')}[/yellow]"
        )
        
        # Add project if available
        if user_config.get('active_project_name'):
            success_msg += f"\n[dim]Project:[/dim] [green]{user_config.get('active_project_name')}[/green]"
        
        console.print(Panel(
            success_msg,
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
        
    except AuthenticationError as e:
        console.print(Panel(
            f"[red]❌ Authentication failed[/red]\n\n"
            f"[dim]Error:[/dim] {str(e)}\n\n"
            "[yellow]Please check your API key and try again[/yellow]",
            title="[bold red]Validation Error[/bold red]",
            border_style="red"
        ))
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(Panel(
            f"[red]❌ Failed to save API key[/red]\n\n"
            f"[dim]Error:[/dim] {str(e)}",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))


def _interactive_set_base_url():
    """Interactive base URL setup"""
    from rich.prompt import Prompt
    from rich.panel import Panel
    from runagent.constants import DEFAULT_BASE_URL
    
    console.print(f"[dim]Current: {Config.get_base_url()}[/dim]")
    console.print(f"[dim]Default: {DEFAULT_BASE_URL}[/dim]\n")
    
    base_url = Prompt.ask(
        "[cyan]Enter base URL[/cyan]",
        default=DEFAULT_BASE_URL
    )
    
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
    
    success = Config.set_base_url(base_url)
    
    if success:
        console.print(Panel(
            f"[bold green]✅ Base URL updated successfully![/bold green]\n\n"
            f"[dim]New URL:[/dim] [cyan]{base_url}[/cyan]",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[red]❌ Failed to save base URL[/red]",
            title="[bold red]Error[/bold red]",
            border_style="red"
        ))


def _interactive_sync_settings():
    """Interactive sync settings configuration"""
    try:
        from rich.panel import Panel
        import inquirer
        
        # Get current status
        user_config = Config.get_user_config()
        current_status = user_config.get('local_sync_enabled', True)
        
        # Show current status
        if current_status:
            status_text = "[green]Currently: ENABLED[/green]"
        else:
            status_text = "[red]Currently: DISABLED[/red]"
        
        console.print(f"\n[bold]Middleware Sync[/bold] {status_text}\n")
        
        # Ask what to do
        questions = [
            inquirer.List(
                'sync_action',
                message="Select sync preference",
                choices=[
                    ('Enable Sync (sync local runs to middleware)', 'enable'),
                    ('Disable Sync (local only)', 'disable'),
                ],
                default=('Enable Sync (sync local runs to middleware)', 'enable') if current_status else ('Disable Sync (local only)', 'disable'),
                carousel=True
            ),
        ]
        
        answers = safe_prompt(questions, "[dim]Sync configuration cancelled.[/dim]")
        if not answers:
            return
        
        action = answers['sync_action']
        
        # Set the preference
        new_status = (action == 'enable')
        Config.set_user_config('local_sync_enabled', new_status)
        
        if new_status:
            console.print(Panel(
                "[bold green]✅ Middleware sync enabled![/bold green]\n\n"
                "[dim]Local agent runs will now sync to middleware.[/dim]\n"
                "[dim]Requires valid API key.[/dim]",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[bold yellow]Middleware sync disabled[/bold yellow]\n\n"
                "[dim]Local agents will only store data locally.[/dim]\n"
                "[dim]Your runs won't appear in the middleware dashboard.[/dim]",
                title="[bold]Sync Disabled[/bold]",
                border_style="yellow"
            ))
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"[red]Error:[/red] {e}")


def _interactive_set_project():
    """Interactive project selection from API"""
    try:
        from rich.panel import Panel
        from rich.status import Status
        import inquirer
        
        # Get API key
        api_key = Config.get_api_key()
        if not api_key:
            console.print(Panel(
                "[red]❌ No API key configured[/red]\n\n"
                "[dim]Run 'runagent setup' first[/dim]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            ))
            return
        
        # Fetch projects from API
        console.print("\n[cyan]Fetching your projects...[/cyan]\n")
        
        from runagent.sdk.rest_client import RestClient
        
        with Status("[bold cyan]Loading projects...", spinner="dots"):
            rest_client = RestClient(
                api_key=api_key,
                base_url=Config.get_base_url()
            )
            
            try:
                response = rest_client.http.get("/projects?page=1&per_page=20&include_stats=false")
                
                if response.status_code != 200:
                    console.print(Panel(
                        f"[red]❌ Failed to fetch projects (Status: {response.status_code})[/red]",
                        title="[bold red]Error[/bold red]",
                        border_style="red"
                    ))
                    return
                
                projects_data = response.json()
                
                if not projects_data.get("success"):
                    console.print(Panel(
                        f"[red]❌ {projects_data.get('error', 'Failed to fetch projects')}[/red]",
                        title="[bold red]Error[/bold red]",
                        border_style="red"
                    ))
                    return
                
                projects = projects_data.get("data", {}).get("projects", [])
                
                if not projects:
                    console.print(Panel(
                        "[yellow]⚠️  No projects found[/yellow]\n\n"
                        "[dim]Create a project in the dashboard first[/dim]",
                        title="[bold]No Projects[/bold]",
                        border_style="yellow"
                    ))
                    return
                
            except Exception as e:
                console.print(Panel(
                    f"[red]❌ Error fetching projects: {str(e)}[/red]",
                    title="[bold red]Error[/bold red]",
                    border_style="red"
                ))
                return
        
        # Show project selection
        current_project_id = Config.get_user_config().get('active_project_id')
        
        project_choices = []
        default_choice = None
        
        for project in projects:
            project_id = project.get('id')
            project_name = project.get('name', 'Unnamed')
            is_default = project.get('is_default', False)
            
            # Mark current and default projects
            label = project_name
            if project_id == current_project_id:
                label = f"✓ {label} [current]"
                default_choice = (label, project_id)
            elif is_default:
                label = f"{label} [default]"
            
            choice_tuple = (label, project_id)
            project_choices.append(choice_tuple)
            
            if not default_choice and is_default:
                default_choice = choice_tuple
        
        questions = [
            inquirer.List(
                'project',
                message="Select active project",
                choices=project_choices,
                default=default_choice,
                carousel=True
            ),
        ]
        
        answers = safe_prompt(questions, "[dim]Project selection cancelled.[/dim]")
        if not answers:
            return
        
        selected_project_id = answers['project']
        
        # Find selected project details
        selected_project = next(
            (p for p in projects if p.get('id') == selected_project_id),
            None
        )
        
        if not selected_project:
            console.print("[red]Error: Project not found[/red]")
            return
        
        # Save to database
        Config.set_user_config('active_project_id', selected_project_id)
        Config.set_user_config('active_project_name', selected_project.get('name'))
        
        console.print(Panel(
            f"[bold green]✅ Active project updated![/bold green]\n\n"
            f"[dim]Project:[/dim] [cyan]{selected_project.get('name')}[/cyan]",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"[red]Error:[/red] {e}")


def _show_config_status():
    """Show configuration status (helper for interactive menu and status command)"""
    from rich.panel import Panel
    from rich.table import Table
    
    user_config = Config.get_user_config()
    api_key = Config.get_api_key()
    base_url = Config.get_base_url()
    
    # Create status table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Setting", style="dim")
    table.add_column("Value", style="cyan")
    
    # API Key status
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        table.add_row("API Key", f"[green]✓[/green] {masked_key}")
    else:
        table.add_row("API Key", "[red]✗ Not set[/red]")
    
    # Base URL
    table.add_row("Base URL", base_url or "[yellow]Using default[/yellow]")
    
    # User info
    if user_config.get('user_email'):
        table.add_row("Email", user_config.get('user_email'))
    
    if user_config.get('user_tier'):
        table.add_row("Tier", user_config.get('user_tier'))
    
    # Active project
    if user_config.get('active_project_name'):
        table.add_row("Active Project", user_config.get('active_project_name'))
    
    # Sync status
    sync_enabled = user_config.get('local_sync_enabled', True)
    if sync_enabled:
        table.add_row("Middleware Sync", "[green]✓ Enabled[/green]")
    else:
        table.add_row("Middleware Sync", "[yellow]Disabled[/yellow]")
    
    console.print(Panel(
        table,
        title="[bold cyan]RunAgent Configuration[/bold cyan]",
        border_style="cyan"
    ))
    
    # Show helpful info
    console.print("\n[dim]Use arrow keys in interactive mode: 'runagent config'[/dim]")
    console.print("[dim]Direct flags for automation: 'runagent config --set-api-key <key>'[/dim]\n")


def _interactive_reset_config():
    """Interactive reset configuration (helper for interactive menu)"""
    from rich.prompt import Confirm
    from rich.panel import Panel
    
    console.print("[yellow]This will remove all your configuration including API key[/yellow]")
    if not Confirm.ask("\n[bold]Are you sure you want to reset?[/bold]", default=False):
        console.print("[dim]Reset cancelled.[/dim]")
        return
    
    sdk = RunAgent()
    sdk.config.clear()
    
    console.print(Panel(
        "[bold green]✅ Configuration reset successfully![/bold green]\n\n"
        "[dim]Run 'runagent setup' to configure again.[/dim]",
        title="[bold green]Success[/bold green]",
        border_style="green"
    ))




@config.command("reset")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def config_reset_cmd(yes):
    """Reset configuration to defaults"""
    if yes:
        _reset_config_without_prompt()
    else:
        _interactive_reset_config()


def _reset_config_without_prompt():
    """Reset config without confirmation (for --yes flag)"""
    from rich.panel import Panel
    
    try:
        sdk = RunAgent()
        sdk.config.clear()
        
        console.print(Panel(
            "[bold green]✅ Configuration reset successfully![/bold green]\n\n"
            "[dim]Run 'runagent setup' to configure again.[/dim]",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"[red]Error:[/red] {e}")
        raise click.ClickException("Reset failed")
