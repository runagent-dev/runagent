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
                    ('⚡ Express Setup (Browser login)', 'express'),
                    ('📝 Manual Setup (Enter API key)', 'manual'),
                ],
                default=('⚡ Express Setup (Browser login)', 'express'),
                carousel=True
            ),
        ]
        
        answers = inquirer.prompt(questions)
        if not answers:
            console.print("[dim]Setup cancelled.[/dim]")
            return
        
        choice = answers['setup_method']
        
        if choice == "express":
            # Express setup - Device code authentication flow
            from runagent.cli.auth.device_flow import DeviceCodeAuthFlow
            from runagent.constants import DEFAULT_BASE_URL
            
            base_url = Config.get_base_url() or DEFAULT_BASE_URL
            
            try:
                flow = DeviceCodeAuthFlow(base_url)
                auth_result = flow.authenticate()
                api_key = auth_result.get("api_key")
                user_info = auth_result.get("user_info", {})
                
                # Save the API key
                if Config.set_api_key(api_key):
                    # Save user info from device auth
                    if user_info:
                        Config.set_user_config("user_email", user_info.get("email"))
                        Config.set_user_config("user_id", user_info.get("user_id"))
                        Config.set_user_config("user_tier", user_info.get("tier", "Free"))
                        Config.set_user_config("active_project_id", user_info.get("active_project_id"))
                        Config.set_user_config("active_project_name", user_info.get("active_project_name"))
                    
                    # Successfully saved, continue to show user info
                    pass
                else:
                    console.print(Panel(
                        "[red]❌ Failed to save credentials[/red]",
                        title="[bold red]Error[/bold red]",
                        border_style="red"
                    ))
                    raise click.ClickException("Failed to save API key")
            
            except click.ClickException:
                raise
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(Panel(
                    f"[red]❌ Setup failed:[/red] {str(e)}",
                    title="[bold red]Error[/bold red]",
                    border_style="red"
                ))
                raise click.ClickException("Express setup failed")
        
        else:
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

