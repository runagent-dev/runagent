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
            import warnings
            from datetime import datetime
            
            # Suppress Pydantic datetime warnings during config update
            warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')
            
            config_path = project_path / "runagent.config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                config_data['name'] = agent_name
                config_data['description'] = agent_description
                
                # Fix created_at format if it exists and is a string in wrong format
                if 'created_at' in config_data and isinstance(config_data['created_at'], str):
                    try:
                        # Try to parse and convert to ISO format
                        dt = datetime.strptime(config_data['created_at'], "%Y-%m-%d %H:%M:%S")
                        config_data['created_at'] = dt.isoformat()
                    except:
                        # If parsing fails, use current time in ISO format
                        config_data['created_at'] = datetime.now().isoformat()
                
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
        console.print(Panel(
            f"[bold red]Template Error[/bold red]\n\n"
            f"{str(e)}\n\n"
            f"[dim]Please check that the selected framework and template are valid.[/dim]",
            title="[bold red]❌ Failed[/bold red]",
            border_style="red"
        ))
        import sys
        sys.exit(1)
    except FileExistsError as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        
        # Extract just the path from the error message
        path_match = str(e).split("'")
        folder_path = path_match[1] if len(path_match) > 1 else "the specified path"
        
        console.print(Panel(
            f"[bold yellow]Directory Already Exists[/bold yellow]\n\n"
            f"[dim]Path:[/dim] [cyan]{folder_path}[/cyan]\n\n"
            f"The directory already exists and is not empty.\n\n"
            f"[bold]Options:[/bold]\n"
            f"  • Choose a different path\n"
            f"  • Use [cyan]--overwrite[/cyan] flag to replace existing files\n"
            f"  • Remove the directory manually",
            title="[bold yellow]⚠️  Path Conflict[/bold yellow]",
            border_style="yellow"
        ))
        import sys
        sys.exit(1)
    except click.UsageError:
        # Re-raise UsageError as-is for proper click handling
        raise
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Initialization error:[/red] {e}")
        raise click.ClickException("Project initialization failed")

