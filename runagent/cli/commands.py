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


def print_version(ctx, param, value):
    """Custom version callback with colored output"""
    if not value or ctx.resilient_parsing:
        return
    try:
        from runagent.__version__ import __version__
        from runagent.cli.branding import print_compact_logo
        print_compact_logo(brand_color="cyan")
        console.print(f"\n[bold white]Version:[/bold white] [bold cyan]{__version__}[/bold cyan]")
        console.print(f"[dim]Deploy and manage AI agents with ease 🚀[/dim]\n")
    except ImportError:
        console.print("[red]runagent version unknown[/red]")
    ctx.exit()


# ============================================================================
# Config Command Group
# ============================================================================

@click.group(invoke_without_command=True)
@click.option("--set-api-key", help="Set API key directly (e.g., runagent config --set-api-key YOUR_KEY)")
@click.option("--set-base-url", help="Set base URL directly (e.g., runagent config --set-base-url https://api.example.com)")
@click.pass_context
def config(ctx, set_api_key, set_base_url):
    """
    Manage RunAgent configuration
    
    \b
    Interactive mode (for humans):
      $ runagent config
    
    \b
    Direct flags (for scripts/agents):
      $ runagent config --set-api-key YOUR_KEY
      $ runagent config --set-base-url https://api.example.com
    
    \b
    Subcommands:
      $ runagent config status
      $ runagent config reset
    """
    
    # Handle direct flag options
    if set_api_key:
        _set_api_key_direct(set_api_key)
        return
    
    if set_base_url:
        _set_base_url_direct(set_base_url)
        return
    
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
                    ('🔑 API Key', 'api_key'),
                    ('🌐 Base URL', 'base_url'),
                    ('📁 Active Project', 'project'),
                    ('🔄 Sync Settings', 'sync'),
                    ('📊 View Status', 'status'),
                    ('🔃 Reset Configuration', 'reset'),
                ],
                carousel=True
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            console.print("[dim]Configuration cancelled.[/dim]")
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
        elif option == 'status':
            _show_config_status()
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
        
        console.print(f"\n📡 Middleware Sync {status_text}\n")
        
        # Ask what to do
        questions = [
            inquirer.List(
                'sync_action',
                message="Select sync preference",
                choices=[
                    ('✅ Enable Sync (sync local runs to middleware)', 'enable'),
                    ('❌ Disable Sync (local only)', 'disable'),
                ],
                default=('✅ Enable Sync (sync local runs to middleware)', 'enable') if current_status else ('❌ Disable Sync (local only)', 'disable'),
                carousel=True
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            console.print("[dim]Sync configuration cancelled.[/dim]")
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
                "[bold yellow]⚠️  Middleware sync disabled[/bold yellow]\n\n"
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
        console.print("\n[cyan]📁 Fetching your projects...[/cyan]\n")
        
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
            label = f"📁 {project_name}"
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
        
        answers = inquirer.prompt(questions)
        if not answers:
            console.print("[dim]Project selection cancelled.[/dim]")
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
        table.add_row("🔑 API Key", f"[green]✓[/green] {masked_key}")
    else:
        table.add_row("🔑 API Key", "[red]✗ Not set[/red]")
    
    # Base URL
    table.add_row("🌐 Base URL", base_url or "[yellow]Using default[/yellow]")
    
    # User info
    if user_config.get('user_email'):
        table.add_row("✉️  Email", user_config.get('user_email'))
    
    if user_config.get('user_tier'):
        table.add_row("🎯 Tier", user_config.get('user_tier'))
    
    # Active project
    if user_config.get('active_project_name'):
        table.add_row("📁 Active Project", user_config.get('active_project_name'))
    
    # Sync status
    sync_enabled = user_config.get('local_sync_enabled', True)
    if sync_enabled:
        table.add_row("🔄 Middleware Sync", "[green]✓ Enabled[/green]")
    else:
        table.add_row("🔄 Middleware Sync", "[yellow]⚠ Disabled[/yellow]")
    
    console.print(Panel(
        table,
        title="[bold cyan]RunAgent Configuration[/bold cyan]",
        border_style="cyan"
    ))
    
    # Show helpful info
    console.print("\n[dim]💡 Use arrow keys in interactive mode: 'runagent config'[/dim]")
    console.print("[dim]💡 Direct flags for automation: 'runagent config --set-api-key <key>'[/dim]\n")


def _interactive_reset_config():
    """Interactive reset configuration (helper for interactive menu)"""
    from rich.prompt import Confirm
    from rich.panel import Panel
    
    console.print("[yellow]⚠️  This will remove all your configuration including API key[/yellow]")
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




@config.command("status")
def config_status_cmd():
    """Show current configuration status"""
    _show_config_status()


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

@click.command()
@click.option("--again", is_flag=True, help="Reconfigure even if already setup")
def setup(again):
    """
    Setup RunAgent authentication
    
    \b
    First-time setup:
      $ runagent setup
    
    \b
    Reconfigure:
      $ runagent setup --again
    
    \b
    Change specific settings later:
      $ runagent config set-api-key
      $ runagent config set-base-url
    """
    try:
        from runagent.cli.branding import print_setup_banner
        from rich.prompt import Prompt, Confirm
        from rich.panel import Panel
        
        sdk = RunAgent()
        api_key = Config.get_api_key()

        # Check if already configured
        if api_key and not again:
            config_status = sdk.get_config_status()
            user_email = config_status.get('user_info', {}).get('email', 'N/A')
            
            console.print(Panel(
                "[bold cyan]✅ RunAgent is already configured![/bold cyan]\n\n"
                f"[dim]User:[/dim] [green]{user_email}[/green]\n"
                f"[dim]Base URL:[/dim] [cyan]{config_status.get('base_url')}[/cyan]\n\n"
                "[dim]To reconfigure, run:[/dim] [white]runagent setup --again[/white]\n"
                "[dim]To view config:[/dim] [white]runagent config status[/white]",
                title="[bold]Already Setup[/bold]",
                border_style="cyan"
            ))
            return

        # Show welcome banner for new setup
        if not api_key or again:
            if not api_key:
                print_setup_banner()
            else:
                console.print("\n[bold cyan]🔄 Reconfiguring RunAgent[/bold cyan]\n")
        
        # Show setup method options with arrow-key selection
        console.print("[bold cyan]Choose your setup method:[/bold cyan]\n")
        
        import inquirer
        
        questions = [
            inquirer.List(
                'setup_method',
                message="Select setup method",
                choices=[
                    ('🪄 Express Setup (Browser login - Coming Soon!)', 'express'),
                    ('🔑 Manual Setup (Enter API key)', 'manual'),
                ],
                default=('🔑 Manual Setup (Enter API key)', 'manual'),
                carousel=True
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            console.print("[dim]Setup cancelled.[/dim]")
            return
        
        choice = answers['setup_method']
        
        if choice == "express":
            # Express setup - coming soon
            console.print(Panel(
                "[bold cyan]🚀 Express Setup - Coming Soon![/bold cyan]\n\n"
                "This feature will allow you to authenticate via your browser.\n\n"
                "[dim]For now, please use Manual Setup[/dim]\n\n"
                "📚 [link=https://docs.runagent.dev/setup]Learn more[/link]",
                title="[bold]Feature Preview[/bold]",
                border_style="cyan"
            ))
            
            if not Confirm.ask("\n[bold]Continue with Manual Setup?[/bold]", default=True):
                console.print("[dim]Setup cancelled.[/dim]")
                return
        
        # Manual setup - prompt for API key
        console.print("\n[bold white]📝 Manual Setup[/bold white]\n")
        api_key = Prompt.ask(
            "[cyan]Enter your API key[/cyan]",
            password=True
        )
        
        if not api_key or not api_key.strip():
            console.print(Panel(
                "[red]❌ API key cannot be empty[/red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            ))
            raise click.ClickException("Invalid API key")
        
        console.print("\n🔑 [cyan]Configuring RunAgent...[/cyan]")

        # Configure SDK with validation
        try:
            from rich.status import Status
            from runagent.constants import DEFAULT_BASE_URL
            
            # Use default base URL from constants
            base_url = Config.get_base_url() or DEFAULT_BASE_URL
            
            with Status("[bold cyan]Validating credentials...", spinner="dots", console=console) as status:
                sdk.configure(api_key=api_key, base_url=base_url, save=True)
            
            console.print(Panel(
                "[bold green]✅ Setup completed successfully![/bold green]\n\n"
                "[dim]Your credentials have been saved securely.[/dim]",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        except AuthenticationError as auth_err:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            console.print(f"❌ [red]Authentication failed:[/red] {auth_err}")
            
            # Provide specific troubleshooting based on error message
            error_msg = str(auth_err).lower()
            console.print("\n💡 [yellow]Troubleshooting:[/yellow]")
            
            if "invalid api key" in error_msg or "not authenticated" in error_msg:
                console.print("   • Check that your API key is correct")
                console.print("   • Verify the API key is not expired")
                console.print("   • Ensure you have access to the middleware")
            elif "connection" in error_msg or "timeout" in error_msg:
                console.print("   • Check your internet connection")
                console.print("   • Verify the middleware server is accessible")
                from runagent.constants import DEFAULT_BASE_URL
                display_url = base_url if 'base_url' in locals() else DEFAULT_BASE_URL
                console.print(f"   • Trying to connect to: {display_url}")
            else:
                console.print("   • Check your API key and network connection")
                console.print("   • Contact support if the issue persists")
            
            raise click.ClickException("Authentication failed")

        # Show user information (from cached data)
        config_status = sdk.get_config_status()
        user_info = config_status.get('user_info', {})
        
        if user_info and user_info.get('email'):
            from rich.panel import Panel
            from rich.table import Table
            
            # Create info table
            info_table = Table(show_header=False, box=None, padding=(0, 2))
            info_table.add_column("", style="dim", no_wrap=True)
            info_table.add_column("", style="cyan")
            
            info_table.add_row("✉️  Email", user_info.get('email'))
            info_table.add_row("🎯 Tier", user_info.get('tier', 'Free'))
            
            # Show active project
            user_config = Config.get_user_config()
            active_project = user_config.get('active_project_name')
            if active_project:
                info_table.add_row("📁 Active Project", active_project)
            
            console.print(Panel(
                info_table,
                title="[bold]👤 User Information[/bold]",
                border_style="cyan"
            ))

        # Show sync status (simplified)
        console.print("\n🔄 [bold]Middleware Sync Status:[/bold]")
        try:
            from runagent.sdk.deployment.middleware_sync import MiddlewareSyncService
            sync_service = MiddlewareSyncService(sdk.config)
            
            if sync_service.is_sync_enabled():
                console.print("   Status: [green]✅ ENABLED[/green]")
                console.print("   📊 Local agent runs will sync to middleware")
            else:
                console.print("   Status: [yellow]⚠️ DISABLED[/yellow]")
                console.print("   📊 Only local storage will be used")
                
        except Exception as e:
            console.print(f"   Status: [yellow]Unknown - {e}[/yellow]")

        # Show next steps - Simple workflow
        console.print("\n💡 [bold]Next Steps:[/bold]")
        console.print("   1️⃣  Initialize a new agent: [cyan]runagent init[/cyan]")
        console.print("   2️⃣  Serve it locally: [cyan]runagent serve <path>[/cyan]")
        console.print("   3️⃣  Invoke your agent: [cyan]runagent run --id <agent-id> --tag <tag>[/cyan]")

    except AuthenticationError:
        # Already handled above
        raise
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Setup error:[/red] {e}")
        raise click.ClickException("Setup failed")


        
@click.command()
@click.option("--yes", is_flag=True, help="Skip confirmation")
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
                "[bold red]⚠️  COMPLETE TEARDOWN[/bold red]\n\n"
                "This will permanently delete:\n"
                "  • All configuration (API key, user info, settings)\n"
                "  • Complete database (all agents, runs, logs, history)\n"
                "  • All local agent data\n\n"
                "[yellow]This action CANNOT be undone![/yellow]",
                title="[bold red]Warning[/bold red]",
                border_style="red"
            ))
            
            console.print("\n📊 [bold]Current data:[/bold]")
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
            console.print(f"🗑️  [dim]Deleted database: {db_path}[/dim]")
        
        # Delete legacy JSON file if exists
        json_file = Path(LOCAL_CACHE_DIRECTORY) / "user_data.json"
        if json_file.exists():
            json_file.unlink()
            console.print(f"🗑️  [dim]Deleted legacy config: {json_file}[/dim]")

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
            console.print("\n💡 Available agents:")
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
        console.print(f"\n🔍 [yellow]Agent to be deleted:[/yellow]")
        console.print(f"   Agent ID: [bold magenta]{agent['agent_id']}[/bold magenta]")
        console.print(f"   Framework: [green]{agent['framework']}[/green]")
        console.print(f"   Path: [blue]{agent['agent_path']}[/blue]")
        console.print(f"   Status: [yellow]{agent['status']}[/yellow]")
        console.print(f"   Deployed: [dim]{agent['deployed_at']}[/dim]")
        console.print(f"   Total Runs: [cyan]{agent['run_count']}[/cyan]")
        
        # Confirmation
        if not yes:
            if not click.confirm("\n⚠️ This will permanently delete the agent from the database. Continue?"):
                console.print("Deletion cancelled.")
                return
        
        # Delete the agent
        result = sdk.db_service.force_delete_agent(agent_id)
        
        if result["success"]:
            console.print(f"\n✅ [green]Agent {agent_id} deleted successfully![/green]")
            
            # Show updated capacity
            capacity_info = sdk.db_service.get_database_capacity_info()
            console.print(f"📊 Updated capacity: [cyan]{capacity_info.get('current_count', 0)}/5[/cyan] agents")
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


@click.command()
@click.option("--template", help="Template variant (default, advanced, etc.) - for non-interactive")
@click.option("--blank", is_flag=True, help="Start from blank template - for non-interactive")
@click.option("--name", help="Agent name - for non-interactive")
@click.option("--description", help="Agent description - for non-interactive")
@click.option("--overwrite", is_flag=True, help="Overwrite existing folder")
@add_framework_options  # Adds framework flags for non-interactive
@click.argument(
    "path",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        path_type=Path,
    ),
    default=".",
    required=False,
)
def init(template, blank, name, description, overwrite, path, **kwargs):
    """
    Initialize a new RunAgent project
    
    \b
    Interactive mode (default - recommended):
      $ runagent init
    
    \b
    Non-interactive with template:
      $ runagent init --framework langgraph --template advanced --name "My Agent" --description "Does XYZ" ./my-agent
    
    \b
    Non-interactive blank:
      $ runagent init --blank --name "Custom Agent" --description "My custom implementation"
    """
    
    try:
        from runagent.cli.branding import print_header
        from rich.prompt import Prompt
        from rich.panel import Panel
        import inquirer
        
        print_header("Initialize Project")
        
        sdk = RunAgent()
        
        # Determine if interactive mode
        selected_framework = get_selected_framework(kwargs)
        has_required_non_interactive = (
            (selected_framework or blank) and name and description
        )
        is_interactive = not has_required_non_interactive
        
        # Variables to collect
        agent_name = name
        agent_description = description
        use_blank = blank
        framework = selected_framework
        selected_template = template or "default"
        
        if is_interactive:
            # Step 1: Choose blank or template
            console.print("[bold cyan]How would you like to start?[/bold cyan]\n")
            
            start_questions = [
                inquirer.List(
                    'start_type',
                    message="Select starting point",
                    choices=[
                        ('📦 From Template (recommended)', 'template'),
                        ('📄 Blank Project (advanced)', 'blank'),
                    ],
                    default=('📦 From Template (recommended)', 'template'),
                    carousel=True
                ),
            ]
            
            start_answer = inquirer.prompt(start_questions)
            if not start_answer:
                console.print("[dim]Initialization cancelled.[/dim]")
                return
            
            use_blank = (start_answer['start_type'] == 'blank')
            
            # Step 2: If template, select framework and template
            if not use_blank:
                # Select framework
                console.print("\n[bold]Select framework:[/bold]\n")
                selectable_frameworks = Framework.get_selectable_frameworks()
                
                framework_choices = []
                for fw in selectable_frameworks:
                    category_emoji = "🐍" if fw.is_pythonic() else "🌐" if fw.is_webhook() else "❓"
                    label = f"{category_emoji} {fw.value} ({fw.category})"
                    framework_choices.append((label, fw))
                
                fw_questions = [
                    inquirer.List(
                        'framework',
                        message="Choose framework",
                        choices=framework_choices,
                        carousel=True
                    ),
                ]
                
                fw_answer = inquirer.prompt(fw_questions)
                if not fw_answer:
                    console.print("[dim]Initialization cancelled.[/dim]")
                    return
                
                framework = fw_answer['framework']
                
                # Select template for chosen framework
                console.print(f"\n[bold]Select template for {framework.value}:[/bold]")
                
                # Fetch templates with real progress feedback
                from rich.status import Status
                import time
                
                fetch_start = time.time()
                
                with Status(
                    "[cyan]Fetching available templates...[/cyan]",
                    console=console,
                    spinner="dots"
                ) as status:
                    clone_start = time.time()
                    status.update("[cyan]Cloning template repository...[/cyan]")
                    
                    templates = sdk.list_templates(framework.value)
                    clone_time = time.time() - clone_start
                    
                    status.update(f"[cyan]Templates fetched ({clone_time:.1f}s)[/cyan]")
                    template_list = templates.get(framework.value, ["default"])
                
                fetch_time = time.time() - fetch_start
                
                console.print(f"[dim]✓ Found {len(template_list)} template(s) in {fetch_time:.1f}s[/dim]")
                
                # Auto-select if only one template available
                if len(template_list) == 1:
                    selected_template = template_list[0]
                    console.print(f"[dim]→ Using template: {selected_template}[/dim]\n")
                else:
                    # Show dropdown for multiple templates
                    console.print()
                    template_choices = [(f"🧱 {tmpl}", tmpl) for tmpl in template_list]
                    
                    tmpl_questions = [
                        inquirer.List(
                            'template',
                            message="Choose template",
                            choices=template_choices,
                            carousel=True
                        ),
                    ]
                    
                    tmpl_answer = inquirer.prompt(tmpl_questions)
                    if not tmpl_answer:
                        console.print("[dim]Initialization cancelled.[/dim]")
                        return
                    
                    selected_template = tmpl_answer['template']
            else:
                # Blank project uses default framework
                framework = Framework.DEFAULT
                selected_template = "default"
            
            # Step 3: Get agent name and description (for both blank and template)
            console.print("\n[bold]Agent Details:[/bold]\n")
            
            agent_name = Prompt.ask(
                "[cyan]Agent name[/cyan]",
                default="my-agent"
            )
            
            agent_description = Prompt.ask(
                "[cyan]Agent description[/cyan]",
                default="My AI agent"
            )
            
            # Step 4: Get path (default based on agent name)
            console.print()
            # Convert agent name to valid directory name (replace spaces with hyphens, lowercase)
            default_path = agent_name.lower().replace(" ", "-").replace("_", "-")
            path_input = Prompt.ask(
                "[cyan]Project path[/cyan]",
                default=default_path
            )
            path = Path(path_input)
        
        # Ensure framework is set
        if not framework:
            framework = Framework.DEFAULT
        
        # Validate framework if it came from string input
        if isinstance(framework, str):
            try:
                framework = Framework.from_string(framework)
            except ValueError as e:
                raise click.UsageError(str(e))
        
        # Use the path as the project location
        project_path = path.resolve()
        
        # Ensure the path exists
        project_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Show configuration summary
        console.print(Panel(
            f"[bold]Project Configuration:[/bold]\n\n"
            f"[dim]Name:[/dim] [cyan]{agent_name}[/cyan]\n"
            f"[dim]Description:[/dim] [white]{agent_description}[/white]\n"
            f"[dim]Framework:[/dim] [magenta]{framework.value}[/magenta]\n"
            f"[dim]Template:[/dim] [yellow]{selected_template}[/yellow]\n"
            f"[dim]Path:[/dim] [blue]{project_path}[/blue]",
            title="[bold cyan]Creating Agent[/bold cyan]",
            border_style="cyan"
        ))
        
        # Initialize project
        success = sdk.init_project(
            folder_path=project_path,
            framework=framework.value,
            template=selected_template,
            overwrite=overwrite
        )
        
        if not success:
            raise Exception("Project initialization failed")
        
        # Update config file with name and description
        try:
            config_path = project_path / "runagent.config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                config_data['name'] = agent_name
                config_data['description'] = agent_description
                
                with open(config_path, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                console.print("\n[dim]✓ Updated agent name and description in config[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not update config: {e}[/yellow]")
        
        # Success message
        relative_path = project_path.relative_to(Path.cwd()) if project_path != Path.cwd() else Path(".")
        
        console.print(Panel(
            f"[bold green]✅ Agent '{agent_name}' created successfully![/bold green]\n\n"
            f"[dim]Location:[/dim] [cyan]{relative_path}[/cyan]\n"
            f"[dim]Framework:[/dim] [magenta]{framework.value}[/magenta]",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
        
        # Simple next steps
        console.print("\n💡 [bold]Next Steps:[/bold]")
        if relative_path != Path("."):
            console.print(f"   1️⃣  [cyan]cd {relative_path}[/cyan]")
            console.print(f"   2️⃣  Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")
            console.print(f"   3️⃣  Serve locally: [cyan]runagent serve .[/cyan]")
        else:
            console.print(f"   1️⃣  Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")
            console.print(f"   2️⃣  Serve locally: [cyan]runagent serve .[/cyan]")
    
    except TemplateError as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Template error:[/red] {e}")
        raise click.ClickException("Project initialization failed")
    except FileExistsError as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Path exists:[/red] {e}")
        console.print("💡 Use [cyan]--overwrite[/cyan] to force initialization")
        raise click.ClickException("Project initialization failed")
    except click.UsageError:
        # Re-raise UsageError as-is for proper click handling
        raise
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Initialization error:[/red] {e}")
        raise click.ClickException("Project initialization failed")


@click.command()
@click.option(
    "--list", "action_list", is_flag=True, help="List all available templates"
)
@click.option(
    "--info", "action_info", is_flag=True, help="Get detailed template information"
)
@click.option("--framework", help="Framework name (required for --info)")
@click.option("--template", help="Template name (required for --info)")
@click.option("--filter-framework", help="Filter templates by framework")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def template(action_list, action_info, framework, template, filter_framework, format):
    """Manage project templates"""
    from runagent.cli.branding import print_header
    print_header("Templates")

    if not action_list and not action_info:
        console.print(
            "❌ Please specify either [cyan]--list[/cyan] or [cyan]--info[/cyan]"
        )
        raise click.ClickException("No action specified")

    try:
        sdk = RunAgent()

        if action_list:
            templates = sdk.list_templates(framework=filter_framework)

            if format == "json":
                console.print(json.dumps(templates, indent=2))
            else:
                console.print("📋 [bold cyan]Available Templates:[/bold cyan]")
                for framework_name, template_list in templates.items():
                    console.print(f"\n🎯 [bold blue]{framework_name}:[/bold blue]")
                    for tmpl in template_list:
                        console.print(f"  • {tmpl}")

                console.print(
                    f"\n💡 Use [cyan]'runagent template --info --framework <fw> --template <tmpl>'[/cyan] for details"
                )

        elif action_info:
            if not framework or not template:
                console.print(
                    "❌ Both [cyan]--framework[/cyan] and [cyan]--template[/cyan] are required for --info"
                )
                raise click.ClickException("Missing required parameters")

            template_info = sdk.get_template_info(framework, template)

            if template_info:
                console.print(
                    f"📋 [bold cyan]Template: {framework}/{template}[/bold cyan]"
                )
                console.print(
                    f"Framework: [magenta]{template_info['framework']}[/magenta]"
                )
                console.print(f"Template: [yellow]{template_info['template']}[/yellow]")

                if "metadata" in template_info:
                    metadata = template_info["metadata"]
                    if "description" in metadata:
                        console.print(f"Description: {metadata['description']}")
                    if "requirements" in metadata:
                        console.print(
                            f"Requirements: {', '.join(metadata['requirements'])}"
                        )

                console.print(f"\n📁 [bold]Structure:[/bold]")
                console.print(f"Files: {', '.join(template_info['files'])}")
                if template_info.get("directories"):
                    console.print(
                        f"Directories: {', '.join(template_info['directories'])}"
                    )

                if "readme" in template_info:
                    console.print(f"\n📖 [bold]README:[/bold]")
                    console.print("-" * 50)
                    console.print(
                        template_info["readme"][:500] + "..."
                        if len(template_info["readme"]) > 500
                        else template_info["readme"]
                    )
                    console.print("-" * 50)

                console.print(f"\n🚀 [bold]To use this template:[/bold]")
                console.print(
                    f"[cyan]runagent init --framework {framework} --template {template}[/cyan]"
                )
            else:
                console.print(
                    f"❌ Template [yellow]{framework}/{template}[/yellow] not found"
                )

                # Show available templates
                templates = sdk.list_templates()
                if framework in templates:
                    console.print(
                        f"Available templates for {framework}: {', '.join(templates[framework])}"
                    )
                else:
                    console.print(
                        f"Available frameworks: {', '.join(templates.keys())}"
                    )

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Template error:[/red] {e}")
        raise click.ClickException("Template operation failed")


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
def upload(path: Path):
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

        console.print(f"📤 [bold]Uploading agent...[/bold]")
        console.print(f"📁 Source: [cyan]{path}[/cyan]")

        # Upload agent (framework auto-detected)
        result = sdk.upload_agent(folder=path)

        if result.get("success"):
            agent_id = result["agent_id"]
            console.print(f"\n✅ [green]Upload successful![/green]")
            console.print(f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]")
            console.print(f"\n💡 [bold]Next step:[/bold]")
            console.print(f"[cyan]runagent start --id {agent_id}[/cyan]")
        else:
            console.print(f"❌ [red]Upload failed:[/red] {format_error_message(result.get('error'))}")
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

        console.print(f"🚀 [bold]Starting agent...[/bold]")
        console.print(f"🆔 Agent ID: [magenta]{agent_id}[/magenta]")

        # Start agent
        result = sdk.start_remote_agent(agent_id, config_dict)

        if result.get("success"):
            console.print(f"\n✅ [green]Agent started successfully![/green]")
            console.print(f"🌐 Endpoint: [link]{result.get('endpoint')}[/link]")
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
def deploy(path: Path):
    """Deploy agent (upload + start) to remote server"""

    try:
        from runagent.cli.branding import print_header
        print_header("Deploy Agent")
        
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

        console.print(f"🎯 [bold]Deploying agent (upload + start)...[/bold]")
        console.print(f"📁 Source: [cyan]{path}[/cyan]")

        # Deploy agent (framework auto-detected)
        result = sdk.deploy_remote(folder=str(path))

        if result.get("success"):
            console.print(f"\n✅ [green]Deployment successful![/green]")
            console.print(f"🆔 Agent ID: [bold magenta]{result.get('agent_id')}[/bold magenta]")
            console.print(f"🌐 Endpoint: [link]{result.get('endpoint')}[/link]")
        else:
            console.print(f"❌ [red]Deployment failed:[/red] {format_error_message(result.get('error'))}")
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
        console.print(f"❌ [red]Deployment error:[/red] {e}")
        import sys
        sys.exit(1)



@click.command()
@click.option("--port", type=int, help="Preferred port (auto-allocated if unavailable)")
@click.option("--host", default="127.0.0.1", help="Host to bind server to")
@click.option("--debug", is_flag=True, help="Run server in debug mode")
@click.option("--replace", help="Replace existing agent with this agent ID")
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
def serve(port, host, debug, replace, no_animation, animation_style, path):
    """Start local FastAPI server with subtle robotic runner animation"""

    try:
        from runagent.cli.branding import print_header
        print_header("Serve Agent Locally")
        
        # Show subtle startup animation
        if not no_animation:
            console.print("\n")
            
            if animation_style == "quick":
                show_quick_runner(duration=1.5)
            else:
                show_subtle_robotic_runner(duration=2.0, style=animation_style)
        
        sdk = RunAgent()
        
        # Handle replace operation
        if replace:
            console.print(f"🔄 [yellow]Replacing agent: {replace}[/yellow]")
            
            # Check if the agent to replace exists
            existing_agent = sdk.db_service.get_agent(replace)
            if not existing_agent:
                console.print(f"⚠️ [yellow]Agent {replace} not found in database[/yellow]")
                console.print("💡 Available agents:")
                agents = sdk.db_service.list_agents()
                for agent in agents[:5]:  # Show first 5
                    console.print(f"   • {agent['agent_id']} ({agent['framework']})")
                raise click.ClickException("Agent to replace not found")
            
            # Generate new agent ID
            import uuid
            new_agent_id = str(uuid.uuid4())
            
            # Get currently used ports to avoid conflicts
            used_ports = []
            all_agents = sdk.db_service.list_agents()
            for agent in all_agents:
                if agent.get('port') and agent['agent_id'] != replace:  # Exclude the agent being replaced
                    used_ports.append(agent['port'])
            
            # Allocate host and port
            from runagent.utils.port import PortManager
            if port and PortManager.is_port_available(host, port):
                allocated_host = host
                allocated_port = port
                console.print(f"🎯 Using specified address: [blue]{allocated_host}:{allocated_port}[/blue]")
            else:
                allocated_host, allocated_port = PortManager.allocate_unique_address(used_ports)
                console.print(f"🔌 Auto-allocated address: [blue]{allocated_host}:{allocated_port}[/blue]")
            
            # Use the existing replace_agent method with proper port allocation
            result = sdk.db_service.replace_agent(
                old_agent_id=replace,
                new_agent_id=new_agent_id,
                agent_path=str(path),
                host=allocated_host,
                port=allocated_port,  # Ensure port is not None
                framework=detect_framework(path).value,
            )
            
            if not result["success"]:
                raise click.ClickException(f"Failed to replace agent: {result['error']}")
            
            console.print(f"✅ [green]Agent replaced successfully![/green]")
            console.print(f"🆔 New Agent ID: [bold magenta]{new_agent_id}[/bold magenta]")
            console.print(f"🔌 Address: [bold blue]{allocated_host}:{allocated_port}[/bold blue]")
            
            # Create server with the new agent ID and allocated host/port
            from runagent.sdk.db import DBService
            db_service = DBService()
            
            server = LocalServer(
                db_service=db_service,
                agent_id=new_agent_id,
                agent_path=path,
                port=allocated_port,
                host=allocated_host,
            )
        else:
            # Normal operation - check capacity if not replacing
            capacity_info = sdk.db_service.get_database_capacity_info()
            if capacity_info["is_full"] and not replace:
                console.print("❌ [red]Database is full![/red]")
                oldest_agent = capacity_info.get("oldest_agent", {})
                if oldest_agent:
                    console.print(f"💡 [yellow]Suggested commands:[/yellow]")
                    console.print(f"   Replace: [cyan]runagent serve {path} --replace {oldest_agent.get('agent_id', '')}[/cyan]")
                    console.print(f"   Delete:  [cyan]runagent delete --id {oldest_agent.get('agent_id', '')}[/cyan]")
                raise click.ClickException("Database at capacity. Use --replace or use 'runagent delete' to free space.")
            
            console.print("⚡ [bold]Starting local server with auto port allocation...[/bold]")
            
            # Use the existing LocalServer.from_path method
            server = LocalServer.from_path(path, port=port, host=host)
        
        # Common server startup code
        allocated_host = server.host
        allocated_port = server.port
        
        console.print(f"🌐 URL: [bold blue]http://{allocated_host}:{allocated_port}[/bold blue]")
        console.print(f"📖 Docs: [link]http://{allocated_host}:{allocated_port}/docs[/link]")

        try:
                        
            sync_service = get_middleware_sync()
            sync_enabled = sync_service.is_sync_enabled()
            api_key_set = bool(Config.get_api_key())
            
            console.print(f"\n🔄 [bold]Middleware Sync Status:[/bold]")
            if sync_enabled:
                console.print(f"   Status: [green]✅ ENABLED[/green]")
                console.print(f"   📊 Local invocations will sync to middleware")
                
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
                console.print(f"   Status: [yellow]⚠️ DISABLED[/yellow]")
                if not api_key_set:
                    console.print(f"   Reason: [yellow]API key not configured[/yellow]")
                    console.print(f"   💡 Setup: [cyan]runagent setup --api-key <key>[/cyan]")
                else:
                    user_disabled = not Config.get_user_config().get("local_sync_enabled", True)
                    if user_disabled:
                        console.print(f"   Reason: [yellow]Disabled by user[/yellow]")
                        console.print(f"   💡 Enable: [cyan]runagent local-sync --enable[/cyan]")
                console.print(f"   📊 Local invocations will only be stored locally")
                
        except Exception as e:
            console.print(f"[dim]Note: Could not check middleware sync status: {e}[/dim]")

        # Start server (this will block)
        server.start(debug=debug)

    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Server error:[/red] {e}")
        raise click.ClickException("Server failed to start")


@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ))
@click.option("--id", "agent_id", help="Agent ID to run")
@click.option("--host", help="Host to connect to (use with --port)")
@click.option("--port", type=int, help="Port to connect to (use with --host)")
@click.option(
    "--input",
    "input_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to input JSON file"
)
@click.option("--local", is_flag=True, help="Run agent locally")
@click.option("--tag", required=True, help="Entrypoint tag to be used")
# @click.option("--generic-stream", is_flag=True, help="Use generic streaming mode")
@click.option("--timeout", type=int, help="Timeout in seconds")
@click.pass_context
def run(ctx, agent_id, host, port, input_file, local, tag, timeout):
    """
    Run an agent with flexible configuration options
    
    Examples:
        # Using agent ID with extra params
        runagent run --agent-id my-agent --param1=value1 --param2=value2
        
        # Using host/port with input file
        runagent run --host localhost --port 8080 --input config.json
        
        # local agent
        runagent run --id d33c497d-d3f5-462e-8ff4-c28d819b92d6  --tag minimal  --local --message=something

        # remote agent
        runagent run --id d33c497d-d3f5-462e-8ff4-c28d819b92d6  --tag minimal  --message=something
    """
    from runagent.cli.branding import print_header
    print_header("Run Agent")
    
    # ============================================
    # VALIDATION 1: Either agent-id OR host/port
    # ============================================
    agent_id_provided = agent_id is not None
    host_port_provided = host is not None or port is not None
    
    if agent_id_provided and host_port_provided:
        raise click.UsageError(
            "Cannot specify both --agent-id and --host/--port. "
            "Choose one approach."
        )
    
    if not agent_id_provided and not host_port_provided:
        raise click.UsageError(
            "Must specify either --agent-id or both --host and --port."
        )

    # If using host/port, both must be provided
    if host_port_provided and (host is None or port is None):
        raise click.UsageError(
            "When using host/port, both --host and --port must be specified."
        )
    
    # ============================================
    # # VALIDATION 2: tag validation
    # # ============================================
    if tag.endswith("_stream"):
        console.print(f"❌ [bold red]Execution failed:[/bold red] Cannot use streaming Entrypoint tag `{tag}` through non-streaming endpoint.")
        return
    
    
    # ============================================
    # VALIDATION 3: Input file OR extra params
    # ============================================
    
    # Parse extra parameters from ctx.args
    extra_params = {}
    invalid_args = []

    for arg in ctx.args:
        if arg.startswith('--') and '=' in arg:
            # Valid format: --key=value
            key, value = arg[2:].split('=', 1)
            extra_params[key] = value
        else:
            # Invalid format
            invalid_args.append(arg)
    
    if invalid_args:
        raise click.UsageError(
            f"Invalid extra arguments: {invalid_args}. "
            "Extra parameters must be in --key=value format."
        )
    
    # Check mutual exclusivity of input file and extra params
    if input_file and extra_params:
        raise click.UsageError(
            "Cannot specify both --input file and extra parameters. "
            "Use either --input config.json OR --param1=value1 --param2=value2"
        )
    
    if not input_file and not extra_params:
        console.print("⚠️  No input file or extra parameters provided. Running with defaults.")
    
    # ============================================
    # DISPLAY CONFIGURATION
    # ============================================
    
    console.print("🚀 RunAgent Configuration:")
    
    # Connection info
    if agent_id:
        console.print(f"   Agent ID: [cyan]{agent_id}[/cyan]")
    else:
        console.print(f"   Host: [cyan]{host}[/cyan]")
        console.print(f"   Port: [cyan]{port}[/cyan]")
    
    # Tag
    # mode = "Generic Streaming" if generic_stream else "Generic"
    console.print(f"   Tag: [magenta]{tag}[/magenta]")
    
    # Local execution
    if local:
        console.print("   Local: [green]Yes[/green]")
    else:
        console.print("   Local: [red]No(Deployed to RunAgent Cloud)[/red]")
    
    # Timeout
    if timeout:
        console.print(f"   Timeout: [yellow]{timeout}s[/yellow]")
    
    # Input configuration
    if input_file:
        console.print(f"   Input file: [blue]{input_file}[/blue]")
        # Load and validate JSON file here
        try:
            import json
            with open(input_file, 'r') as f:
                input_params = json.load(f)
            console.print(f"   Config keys: [dim]{list(input_params.keys())}[/dim]")
        except json.JSONDecodeError:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            raise click.ClickException(f"Invalid JSON in input file: {input_file}")
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            raise click.ClickException(f"Error reading input file: {e}")
    
    elif extra_params:
        console.print("   Extra parameters:")
        for key, value in extra_params.items():
            # Try to parse value as JSON for complex types
            # TODO: Will add type inference later
            console.print(f"     --{key} = [green]{value}[/green]")
        input_params = extra_params
    
    else:
        input_params = {}
    
    # ============================================
    # EXECUTION LOGIC
    # ============================================
    
    try:
        ra_client = RunAgentClient(
            agent_id=agent_id,
            local=local,
            host=host,
            port=port,
            entrypoint_tag=tag
        )

        if tag.endswith("_stream"):
            for item in ra_client.run(**input_params):
                console.print(item)
        else:
            result = ra_client.run(**input_params)
            console.print(result)
            
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        # Display error with red ❌ symbol
        console.print(f"❌ [bold red]Execution failed:[/bold red] {e}")
        # Exit with error code 1 instead of raising ClickException to avoid duplicate message
        import sys
        sys.exit(1)


@click.command(
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ))
@click.option("--id", "agent_id", help="Agent ID to run")
@click.option("--host", help="Host to connect to (use with --port)")
@click.option("--port", type=int, help="Port to connect to (use with --host)")
@click.option(
    "--input",
    "input_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to input JSON file"
)
@click.option("--local", is_flag=True, help="Run agent locally")
@click.option("--tag", required=True, help="Entrypoint tag to be used")
@click.option("--timeout", type=int, help="Timeout in seconds")
@click.pass_context
def run_stream(ctx, agent_id, host, port, input_file, local, tag, timeout):
    """
    Stream agent execution results in real-time.
    
    This command connects to an agent via WebSocket and streams the execution results
    as they become available, providing real-time feedback.
    
    Examples:
        # Local streaming agent
        runagent run-stream --id d33c497d-d3f5-462e-8ff4-c28d819b92d6 --tag minimal_stream --local --message=something
        
        # Remote streaming agent
        runagent run-stream --id d33c497d-d3f5-462e-8ff4-c28d819b92d6 --tag minimal_stream --message=something
        
        # With input file
        runagent run-stream --id d33c497d-d3f5-462e-8ff4-c28d819b92d6 --tag minimal_stream --local --input config.json
    """
    from runagent.cli.branding import print_header
    print_header("Stream Agent Output")
    
    # ============================================
    # PARAMETER PARSING
    # ============================================
    
    extra_params = {}
    for item in ctx.args:
        if '=' in item:
            key, value = item.split('=', 1)
            # Remove leading dashes
            key = key.lstrip('-')
            extra_params[key] = value
        else:
            # Handle boolean flags
            key = item.lstrip('-')
            extra_params[key] = True
    
    # ============================================
    # VALIDATION
    # ============================================
    
    # VALIDATION 1: Agent ID or host/port required
    if not agent_id and not (host and port):
        console.print(f"❌ [bold red]Execution failed:[/bold red] Either --id or both --host and --port are required")
        import sys
        sys.exit(1)
    
    # VALIDATION 2: tag validation for streaming
    if not tag.endswith("_stream"):
        console.print(f"❌ [bold red]Execution failed:[/bold red] Streaming command requires entrypoint tag ending with '_stream'. Got: {tag}")
        import sys
        sys.exit(1)
    
    # ============================================
    # DISPLAY CONFIGURATION
    # ============================================
    
    console.print("🚀 RunAgent Streaming Configuration:")
    
    # Connection info
    if agent_id:
        console.print(f"   Agent ID: [cyan]{agent_id}[/cyan]")
    else:
        console.print(f"   Host: [cyan]{host}[/cyan]")
        console.print(f"   Port: [cyan]{port}[/cyan]")
    
    # Tag
    console.print(f"   Tag: [magenta]{tag}[/magenta]")
    
    # Local execution
    if local:
        console.print("   Local: [green]Yes[/green]")
    else:
        console.print("   Local: [red]No (Deployed to RunAgent Cloud)[/red]")
    
    # Timeout
    if timeout:
        console.print(f"   Timeout: [yellow]{timeout}s[/yellow]")
    
    # Input configuration
    if input_file:
        console.print(f"   Input file: [blue]{input_file}[/blue]")
        # Load and validate JSON file here
        try:
            import json
            with open(input_file, 'r') as f:
                input_params = json.load(f)
            console.print(f"   Config keys: [dim]{list(input_params.keys())}[/dim]")
        except json.JSONDecodeError:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            console.print(f"❌ [bold red]Execution failed:[/bold red] Invalid JSON in input file: {input_file}")
            import sys
            sys.exit(1)
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            console.print(f"❌ [bold red]Execution failed:[/bold red] Error reading input file: {e}")
            import sys
            sys.exit(1)
    
    elif extra_params:
        console.print("   Extra parameters:")
        for key, value in extra_params.items():
            console.print(f"     --{key} = {value}")
        input_params = extra_params
    
    else:
        input_params = {}
    
    # ============================================
    # EXECUTION LOGIC
    # ============================================
    
    try:
        ra_client = RunAgentClient(
            agent_id=agent_id,
            local=local,
            host=host,
            port=port,
            entrypoint_tag=tag
        )

        console.print(f"\n🔄 [bold]Starting streaming execution...[/bold]")
        console.print(f"📡 [dim]Connected to agent via WebSocket[/dim]")
        console.print(f"📤 [dim]Streaming results:[/dim]\n")
        
        # Stream the results
        for chunk in ra_client.run_stream(**input_params):
            console.print(chunk)
            
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        # Display error with red ❌ symbol
        console.print(f"❌ [bold red]Streaming failed:[/bold red] {e}")
        # Exit with error code 1 instead of raising ClickException to avoid duplicate message
        import sys
        sys.exit(1)


@click.group()
def db():
    """Database management and monitoring commands"""
    pass

@db.command()
@click.option("--cleanup-days", type=int, help="Clean up records older than N days")
@click.option("--agent-id", help="Show detailed info for specific agent")
@click.option("--capacity", is_flag=True, help="Show detailed capacity information")
def status(cleanup_days, agent_id, capacity):
    """Show local database status and statistics (ENHANCED with invocation stats)"""
    try:
        sdk = RunAgent()

        if capacity:
            # Show detailed capacity info
            capacity_info = sdk.db_service.get_database_capacity_info()

            console.print(f"\n📊 [bold]Database Capacity Information[/bold]")
            console.print(
                f"Current: [cyan]{capacity_info.get('current_count', 0)}/5[/cyan] agents"
            )
            console.print(
                f"Remaining slots: [green]{capacity_info.get('remaining_slots', 0)}[/green]"
            )

            status = "🔴 FULL" if capacity_info.get("is_full") else "🟢 Available"
            console.print(f"Status: {status}")

            agents = capacity_info.get("agents", [])
            if agents:
                console.print(f"\n📋 [bold]Deployed Agents (by age):[/bold]")
                
                # Create table for agents
                table = Table(title="Agents by Deployment Age")
                table.add_column("#", style="dim", width=3)
                table.add_column("Status", width=6)
                table.add_column("Agent ID", style="magenta", width=36)
                table.add_column("Framework", style="green", width=12)
                table.add_column("Deployed At", style="cyan", width=20)
                table.add_column("Age Note", style="yellow", width=10)
                
                for i, agent in enumerate(agents):
                    status_icon = (
                        "🟢"
                        if agent["status"] == "deployed"
                        else "🔴" if agent["status"] == "error" else "🟡"
                    )
                    age_label = (
                        "oldest"
                        if i == 0
                        else "newest" if i == len(agents) - 1 else ""
                    )
                    
                    table.add_row(
                        str(i+1),
                        status_icon,
                        agent['agent_id'],
                        agent['framework'],
                        agent['deployed_at'] or "Unknown",
                        age_label
                    )
                
                console.print(table)

            if capacity_info.get("is_full"):
                oldest = capacity_info.get("oldest_agent", {})
                console.print(
                    f"\n💡 [yellow]To deploy new agent, replace oldest:[/yellow]"
                )
                console.print(
                    f"   [cyan]runagent serve --folder <path> --replace {oldest.get('agent_id', '')}[/cyan]"
                )
                console.print(
                    f"   [cyan]runagent delete --id {oldest.get('agent_id', '')}[/cyan]"
                )

            return

        if agent_id:
            # Show agent-specific details including invocations
            result = sdk.get_agent_info(agent_id, local=True)
            if result.get("success"):
                agent_data = result["agent_info"]
                console.print(f"\n🔍 [bold]Agent Details: {agent_id}[/bold]")
                console.print(f"Framework: [green]{agent_data.get('framework')}[/green]")
                console.print(f"Status: [yellow]{agent_data.get('status')}[/yellow]")
                console.print(f"Path: [blue]{agent_data.get('deployment_path')}[/blue]")
                
                # Show agent-specific invocation stats
                agent_inv_stats = sdk.db_service.get_invocation_stats(agent_id=agent_id)
                console.print(f"\n📊 [bold]Invocation Statistics for {agent_id}[/bold]")
                console.print(f"Total: [cyan]{agent_inv_stats.get('total_invocations', 0)}[/cyan]")
                console.print(f"Success Rate: [blue]{agent_inv_stats.get('success_rate', 0)}%[/blue]")
                
            return

        # Show general database stats
        stats = sdk.db_service.get_database_stats()
        capacity_info = sdk.db_service.get_database_capacity_info()

        console.print("\n📊 [bold]Local Database Status[/bold]")

        current_count = capacity_info.get("current_count", 0)
        is_full = capacity_info.get("is_full", False)
        status = "FULL" if is_full else "OK"
        console.print(
            f"Agent Capacity: [cyan]{current_count}/5[/cyan] agents ([red]{status}[/red])"
            if is_full
            else f"Agent Capacity: [cyan]{current_count}/5[/cyan] agents ([green]{status}[/green])"
        )

        console.print(f"Total Agent Runs: [cyan]{stats.get('total_runs', 0)}[/cyan]")
        console.print(
            f"Database Size: [yellow]{stats.get('database_size_mb', 0)} MB[/yellow]"
        )

        # NEW: Show invocation statistics
        overall_stats = sdk.db_service.get_invocation_stats()
        
        console.print(f"\n📊 [bold]Invocation Statistics[/bold]")
        console.print(f"Total Invocations: [cyan]{overall_stats.get('total_invocations', 0)}[/cyan]")
        console.print(f"Completed: [green]{overall_stats.get('completed_invocations', 0)}[/green]")
        console.print(f"Failed: [red]{overall_stats.get('failed_invocations', 0)}[/red]")
        console.print(f"Pending: [yellow]{overall_stats.get('pending_invocations', 0)}[/yellow]")
        console.print(f"Success Rate: [blue]{overall_stats.get('success_rate', 0)}%[/blue]")
        
        if overall_stats.get('avg_execution_time_ms'):
            avg_time = overall_stats['avg_execution_time_ms']
            if avg_time < 1000:
                time_display = f"{avg_time:.1f}ms"
            else:
                time_display = f"{avg_time/1000:.2f}s"
            console.print(f"Average Execution Time: [cyan]{time_display}[/cyan]")

        # Show agent status breakdown
        status_counts = stats.get("agent_status_counts", {})
        if status_counts:
            console.print("\n📈 [bold]Agent Status Breakdown:[/bold]")
            for status, count in status_counts.items():
                console.print(f"  [cyan]{status}[/cyan]: {count}")

        # List agents in table format
        agents = sdk.db_service.list_agents()

        if agents:
            console.print(f"\n📋 [bold]Deployed Agents:[/bold]")
            
            # Create table for better formatting
            table = Table(title=f"Local Agents ({len(agents)} total)")
            table.add_column("Status", width=8)
            table.add_column("Files", width=6)
            table.add_column("Agent ID", style="magenta", width=36)
            table.add_column("Framework", style="green", width=12)
            table.add_column("Host:Port", style="blue", width=15)
            table.add_column("Runs", style="cyan", width=6)
            table.add_column("Status", style="yellow", width=10)
            
            for agent in agents:
                status_icon = (
                    "🟢"
                    if agent["status"] == "deployed"
                    else "🔴" if agent["status"] == "error" else "🟡"
                )
                exists_icon = "📁" if agent.get("exists") else "❌"
                
                table.add_row(
                    status_icon,
                    exists_icon,
                    agent['agent_id'],
                    agent['framework'],
                    f"{agent.get('host', 'N/A')}:{agent.get('port', 'N/A')}",
                    str(agent.get('run_count', 0)),
                    agent['status']
                )
            
            console.print(table)

        # Show recent invocations
        recent_invocations = sdk.db_service.list_invocations(limit=5)
        if recent_invocations:
            console.print(f"\n📋 [bold]Recent Invocations:[/bold]")
            for inv in recent_invocations:
                status_color = "green" if inv['status'] == "completed" else "red" if inv['status'] == "failed" else "yellow"
                console.print(f"   • {inv['invocation_id'][:12]}... [{status_color}]{inv['status']}[/{status_color}] ({inv.get('entrypoint_tag', 'N/A')})")

        console.print(f"\n💡 [bold]Database Commands:[/bold]")
        console.print(f"   • [cyan]runagent db invocations[/cyan] - Show all invocations")
        console.print(f"   • [cyan]runagent db invocation <id>[/cyan] - Show specific invocation")
        console.print(f"   • [cyan]runagent db cleanup[/cyan] - Clean up old records")
        console.print(f"   • [cyan]runagent db status --agent-id <id>[/cyan] - Agent-specific info")
        console.print(f"   • [cyan]runagent db status --capacity[/cyan] - Capacity management info")

        # Cleanup if requested (keep existing logic)
        if cleanup_days:
            console.print(f"\n🧹 Cleaning up records older than {cleanup_days} days...")
            cleanup_result = sdk.cleanup_local_database(cleanup_days)
            if cleanup_result.get("success"):
                console.print(f"✅ [green]{cleanup_result.get('message')}[/green]")
            else:
                console.print(f"❌ [red]{cleanup_result.get('error')}[/red]")

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Database status error:[/red] {e}")
        raise click.ClickException("Failed to get database status")


@db.command()
@click.option("--agent-id", help="Filter by specific agent ID")
@click.option("--status", type=click.Choice(["pending", "completed", "failed"]), help="Filter by status")
@click.option("--limit", type=int, default=20, help="Maximum number of invocations to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def invocations(agent_id, status, limit, output_format):
    """Show agent invocation history and statistics"""
    try:
        sdk = RunAgent()
        
        # Get invocations
        invocations_list = sdk.db_service.list_invocations(
            agent_id=agent_id,
            status=status,
            limit=limit
        )
        
        if output_format == "json":
            console.print(json.dumps(invocations_list, indent=2))
            return
        
        if not invocations_list:
            console.print("📭 [yellow]No invocations found[/yellow]")
            if agent_id:
                console.print(f"   • Agent ID: {agent_id}")
            if status:
                console.print(f"   • Status: {status}")
            return
        
        # Show statistics first
        if agent_id:
            stats = sdk.db_service.get_invocation_stats(agent_id=agent_id)
        else:
            stats = sdk.db_service.get_invocation_stats()
        
        console.print(f"\n📊 [bold]Invocation Statistics[/bold]")
        if agent_id:
            console.print(f"   Agent ID: [magenta]{agent_id}[/magenta]")
        console.print(f"   Total: [cyan]{stats.get('total_invocations', 0)}[/cyan]")
        console.print(f"   Completed: [green]{stats.get('completed_invocations', 0)}[/green]")
        console.print(f"   Failed: [red]{stats.get('failed_invocations', 0)}[/red]")
        console.print(f"   Pending: [yellow]{stats.get('pending_invocations', 0)}[/yellow]")
        console.print(f"   Success Rate: [blue]{stats.get('success_rate', 0)}%[/blue]")
        if stats.get('avg_execution_time_ms'):
            console.print(f"   Avg Execution Time: [cyan]{stats.get('avg_execution_time_ms', 0):.1f}ms[/cyan]")
        
        # Show invocations table
        console.print(f"\n📋 [bold]Recent Invocations (showing {len(invocations_list)} of {limit} max)[/bold]")
        
        table = Table(title="Agent Invocations")
        table.add_column("Invocation", style="dim", width=12)
        table.add_column("Agent", style="magenta", width=12)
        table.add_column("Entrypoint", style="green", width=12)
        table.add_column("Status", width=10)
        table.add_column("Duration", style="cyan", width=10)
        table.add_column("Started", style="dim", width=16)
        table.add_column("SDK", style="yellow", width=10)
        
        for inv in invocations_list:
            # Status with color
            status_text = inv['status']
            if status_text == "completed":
                status_display = f"[green]{status_text}[/green]"
            elif status_text == "failed":
                status_display = f"[red]{status_text}[/red]"
            else:
                status_display = f"[yellow]{status_text}[/yellow]"
            
            # Duration calculation
            duration_display = "N/A"
            if inv.get('execution_time_ms'):
                if inv['execution_time_ms'] < 1000:
                    duration_display = f"{inv['execution_time_ms']:.0f}ms"
                else:
                    duration_display = f"{inv['execution_time_ms']/1000:.1f}s"
            
            # Format timestamp
            started_display = "N/A"
            if inv.get('request_timestamp'):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(inv['request_timestamp'].replace('Z', '+00:00'))
                    started_display = dt.strftime('%m-%d %H:%M:%S')
                except:
                    started_display = inv['request_timestamp'][:16]
            
            table.add_row(
                inv['invocation_id'][:8] + "...",
                inv['agent_id'][:8] + "...",
                inv.get('entrypoint_tag', 'N/A')[:12],
                status_display,
                duration_display,
                started_display,
                inv.get('sdk_type', 'unknown')[:10]
            )
        
        console.print(table)
        
        # Show usage tips
        console.print(f"\n💡 [dim]Usage tips:[/dim]")
        console.print(f"   • View specific invocation: [cyan]runagent db invocation <invocation_id>[/cyan]")
        console.print(f"   • Filter by agent: [cyan]runagent db invocations --agent-id <agent_id>[/cyan]")
        console.print(f"   • Filter by status: [cyan]runagent db invocations --status completed[/cyan]")
        console.print(f"   • JSON output: [cyan]runagent db invocations --format json[/cyan]")
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error getting invocations:[/red] {e}")
        raise click.ClickException("Failed to get invocations")


@db.command()
@click.argument("invocation_id")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def invocation(invocation_id, output_format):
    """Show detailed information about a specific invocation"""
    try:
        sdk = RunAgent()
        
        invocation = sdk.db_service.get_invocation(invocation_id)
        
        if not invocation:
            console.print(f"❌ [red]Invocation {invocation_id} not found[/red]")
            
            # Show available invocations
            console.print("\n💡 Recent invocations:")
            recent = sdk.db_service.list_invocations(limit=5)
            for inv in recent:
                console.print(f"   • {inv['invocation_id']} ({inv['status']})")
            
            raise click.ClickException("Invocation not found")
        
        if output_format == "json":
            console.print(json.dumps(invocation, indent=2))
            return
        
        # Display detailed information
        console.print(f"\n🔍 [bold]Invocation Details[/bold]")
        console.print(f"   Invocation ID: [bold magenta]{invocation['invocation_id']}[/bold magenta]")
        console.print(f"   Agent ID: [bold cyan]{invocation['agent_id']}[/bold cyan]")
        console.print(f"   Entrypoint: [green]{invocation.get('entrypoint_tag', 'N/A')}[/green]")
        console.print(f"   SDK Type: [yellow]{invocation.get('sdk_type', 'unknown')}[/yellow]")
        
        # Status with color
        status = invocation['status']
        if status == "completed":
            status_display = f"[green]{status}[/green]"
        elif status == "failed":
            status_display = f"[red]{status}[/red]"
        else:
            status_display = f"[yellow]{status}[/yellow]"
        console.print(f"   Status: {status_display}")
        
        # Timing information
        console.print(f"\n⏱️ [bold]Timing Information[/bold]")
        if invocation.get('request_timestamp'):
            console.print(f"   Started: [cyan]{invocation['request_timestamp']}[/cyan]")
        if invocation.get('response_timestamp'):
            console.print(f"   Completed: [cyan]{invocation['response_timestamp']}[/cyan]")
        if invocation.get('execution_time_ms'):
            exec_time = invocation['execution_time_ms']
            if exec_time < 1000:
                time_display = f"{exec_time:.1f}ms"
            else:
                time_display = f"{exec_time/1000:.2f}s"
            console.print(f"   Duration: [green]{time_display}[/green]")
        
        # Input data
        console.print(f"\n📥 [bold]Input Data[/bold]")
        if invocation.get('input_data'):
            input_str = json.dumps(invocation['input_data'], indent=2)
            if len(input_str) > 500:
                console.print(f"   [dim]{input_str[:500]}...\n   (truncated - use --format json for full data)[/dim]")
            else:
                console.print(f"   [dim]{input_str}[/dim]")
        else:
            console.print("   [dim]No input data[/dim]")
        
        # Output data or error
        if invocation['status'] == 'failed' and invocation.get('error_detail'):
            console.print(f"\n❌ [bold red]Error Details[/bold red]")
            console.print(f"   [red]{invocation['error_detail']}[/red]")
        elif invocation.get('output_data'):
            console.print(f"\n📤 [bold]Output Data[/bold]")
            output_str = json.dumps(invocation['output_data'], indent=2)
            if len(output_str) > 500:
                console.print(f"   [dim]{output_str[:500]}...\n   (truncated - use --format json for full data)[/dim]")
            else:
                console.print(f"   [dim]{output_str}[/dim]")
        
        # Client info
        if invocation.get('client_info'):
            console.print(f"\n🔧 [bold]Client Information[/bold]")
            client_str = json.dumps(invocation['client_info'], indent=2)
            console.print(f"   [dim]{client_str}[/dim]")
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error getting invocation details:[/red] {e}")
        raise click.ClickException("Failed to get invocation details")


@db.command()
@click.option("--days", type=int, default=30, help="Clean up invocations older than N days")
@click.option("--agent-runs", is_flag=True, help="Also clean up old agent_runs records")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def cleanup(days, agent_runs, yes):
    """Clean up old database records"""
    try:
        sdk = RunAgent()
        
        # Get count of records to be cleaned
        all_invocations = sdk.db_service.list_invocations(limit=1000)
        
        # Filter by date (simple approximation for preview)
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_invocations_count = len([
            inv for inv in all_invocations 
            if inv.get('request_timestamp') and 
            datetime.fromisoformat(inv['request_timestamp'].replace('Z', '+00:00')) < cutoff_date
        ])
        
        console.print(f"🧹 [yellow]Cleanup Preview (older than {days} days):[/yellow]")
        console.print(f"   • Invocations: {old_invocations_count} records")
        
        if agent_runs:
            console.print(f"   • Agent runs: Will be cleaned too")
        
        if old_invocations_count == 0:
            console.print(f"✅ [green]No records found older than {days} days[/green]")
            return
        
        if not yes:
            if not click.confirm(f"⚠️ This will permanently delete {old_invocations_count} invocation records. Continue?"):
                console.print("Cleanup cancelled.")
                return
        
        # Perform cleanup
        deleted_invocations = sdk.db_service.cleanup_old_invocations(days_old=days)
        
        console.print(f"✅ [green]Cleaned up {deleted_invocations} old invocation records[/green]")
        
        if agent_runs:
            deleted_runs = sdk.cleanup_local_database(days)
            if deleted_runs.get("success"):
                console.print(f"✅ [green]Also cleaned up old agent runs[/green]")
        
        # Show updated stats
        stats = sdk.db_service.get_invocation_stats()
        console.print(f"📊 Remaining invocations: [cyan]{stats.get('total_invocations', 0)}[/cyan]")
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error cleaning up records:[/red] {e}")
        raise click.ClickException("Cleanup failed")


# local-sync command removed - sync settings now managed via 'runagent config'
# Use: runagent config > Select "🔄 Sync Settings"


# Add this simplified logs command to the db group in runagent/cli/commands.py

@db.command()
@click.option("--agent-id", help="Filter by specific agent ID")
@click.option("--limit", type=int, default=100, help="Maximum number of logs to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
def logs(agent_id, limit, output_format):
    """Show all agent logs (no filtering)"""
    try:
        sdk = RunAgent()
        
        if agent_id:
            # Show logs for specific agent
            logs = sdk.db_service.get_agent_logs(agent_id=agent_id, limit=limit)
            
            if not logs:
                console.print("📭 [yellow]No logs found[/yellow]")
                console.print(f"   • Agent ID: {agent_id}")
                return
            
            if output_format == "json":
                console.print(json.dumps(logs, indent=2))
                return
            
            console.print(f"\n📋 [bold]Agent Logs: {agent_id}[/bold]")
            
            table = Table(title=f"All Agent Logs (showing {len(logs)} entries)")
            table.add_column("Time", style="dim", width=16)
            table.add_column("Level", width=8)
            table.add_column("Message", style="white", width=80)
            table.add_column("Execution", style="cyan", width=12)
            
            for log in logs:
                # Format timestamp
                time_str = "N/A"
                if log.get('created_at'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(log['created_at'])
                        time_str = dt.strftime('%m-%d %H:%M:%S')
                    except:
                        time_str = log['created_at'][:16]
                
                # Color code log levels
                level = log.get('log_level', 'INFO')
                if level == 'ERROR' or level == 'CRITICAL':
                    level_display = f"[red]{level}[/red]"
                elif level == 'WARNING':
                    level_display = f"[yellow]{level}[/yellow]"
                elif level == 'DEBUG':
                    level_display = f"[dim]{level}[/dim]"
                else:
                    level_display = f"[green]{level}[/green]"
                
                # Don't truncate messages - show full log
                message = log.get('message', '')
                
                # Show execution ID if available
                exec_id = log.get('execution_id', '')
                exec_display = exec_id[:8] + "..." if exec_id else ""
                
                table.add_row(time_str, level_display, message, exec_display)
            
            console.print(table)
            
        else:
            # Show log summary for all agents
            agents = sdk.db_service.list_agents()
            
            if not agents:
                console.print("📭 [yellow]No agents found[/yellow]")
                return
            
            console.print(f"\n📊 [bold]Agent Log Summary[/bold]")
            
            table = Table(title="Log Counts by Agent")
            table.add_column("Agent ID", style="magenta", width=36)
            table.add_column("Framework", style="green", width=12)
            table.add_column("Total Logs", style="cyan", width=10)
            table.add_column("Errors", style="red", width=8)
            table.add_column("Last Log", style="dim", width=16)
            
            for agent in agents[:10]:  # Show first 10 agents
                agent_logs = sdk.db_service.get_agent_logs(agent['agent_id'], limit=1000)
                error_logs = [log for log in agent_logs if log.get('log_level') in ['ERROR', 'CRITICAL']]
                
                last_log_time = "Never"
                if agent_logs:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(agent_logs[0]['created_at'])
                        last_log_time = dt.strftime('%m-%d %H:%M')
                    except:
                        last_log_time = "Recent"
                
                table.add_row(
                    agent['agent_id'],
                    agent['framework'],
                    str(len(agent_logs)),
                    str(len(error_logs)),
                    last_log_time
                )
            
            console.print(table)
        
        console.print(f"\n💡 [bold]Usage tips:[/bold]")
        console.print(f"   • View agent logs: [cyan]runagent db logs --agent-id <agent_id>[/cyan]")
        console.print(f"   • JSON output: [cyan]runagent db logs --agent-id <agent_id> --format json[/cyan]")
        console.print(f"   • More logs: [cyan]runagent db logs --agent-id <agent_id> --limit 500[/cyan]")

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error getting logs:[/red] {e}")
        raise click.ClickException("Failed to get logs")


@db.command()
@click.option("--days", type=int, default=7, help="Clean up logs older than N days")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def cleanup_logs(days, yes):
    """Clean up old agent logs"""
    try:
        sdk = RunAgent()
        
        if not yes:
            if not click.confirm(f"⚠️ This will delete logs older than {days} days for ALL agents. Continue?"):
                console.print("Cleanup cancelled.")
                return
        
        deleted_count = sdk.db_service.cleanup_old_logs(days_old=days)
        console.print(f"✅ [green]Cleaned up {deleted_count} old log entries[/green]")
        
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Error cleaning up logs:[/red] {e}")
        raise click.ClickException("Log cleanup failed")