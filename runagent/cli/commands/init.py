import json
import os
import warnings
from datetime import datetime
from pathlib import Path

import click
import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from runagent.cli.branding import print_header
from runagent.cli.utils import add_framework_options, get_selected_framework, safe_prompt
from runagent.constants import AGENT_CONFIG_FILE_NAME, TEMPLATE_REPO_URL
from runagent.sdk import RunAgent
from runagent.sdk.db import DBService
from runagent.sdk.exceptions import TemplateError
from runagent.utils.agent import get_agent_config, get_agent_config_with_defaults
from runagent.utils.agent_id import generate_agent_id, generate_config_fingerprint
from runagent.utils.enums.framework import Framework
from runagent.utils.schema import RunAgentConfig, TemplateSource

console = Console()


@click.command()
@click.option("--template", default="default", help="Template variant (default, advanced, etc.) - for non-interactive")
@click.option("--minimal", is_flag=True, help="Start from minimal template - for non-interactive")
@click.option("--existing", is_flag=True, help="Initialize existing codebase as RunAgent project - for non-interactive")
@click.option("--from-template", help="Specific template to use (e.g., langchain/problem_solver)")
@click.option("--use-auth", type=click.Choice(['none', 'api_key']), help="Authentication type to use")
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
def init(path, template, minimal, existing, from_template, use_auth, name, description, overwrite, **kwargs):
    """
    Initialize a new RunAgent project
    
    \b
    Interactive mode (default - recommended):
      $ runagent init
    
    \b
    Non-interactive examples:
      $ runagent init . --minimal --name "My Agent" --description "Does XYZ"
      $ runagent init /path/to/existing --existing --name "My Agent" --description "Does XYZ"
      $ runagent init . --from-template langchain/problem_solver
      $ runagent init . --langgraph --template advanced --name "My Agent"
      $ runagent init /path/to/project --use-auth api_key
    """
    
    try:
        print_header("Initialize Project")
        
        sdk = RunAgent()
        
        # Determine project path
        project_path = path.resolve()
        if project_path.name == ".":
            project_path = project_path.parent
        
        # Determine if interactive mode
        has_non_interactive_options = (
            minimal or existing or from_template or 
            (name and description) or use_auth
        )
        is_interactive = not has_non_interactive_options
        
        # Variables to collect
        agent_name = name
        agent_description = description
        auth_type = use_auth or "none"
        template_source = None
        selected_template = None
        framework = None
        
        if is_interactive:
            # Step 1: Choose project type
            console.print("[bold cyan]How would you like to start?[/bold cyan]\n")
            
            start_questions = [
                inquirer.List(
                    'start_type',
                    message="Select starting point",
                    choices=[
                        ('Existing Codebase', 'existing'),
                        ('Minimal Project', 'minimal'),
                        ('From Template (recommended)', 'template'),
                    ],
                    default=('From Template (recommended)', 'template'),
                    carousel=True
                ),
            ]
            
            start_answer = safe_prompt(start_questions, "[dim]Initialization cancelled.[/dim]")
            if not start_answer:
                return
            
            start_type = start_answer['start_type']
            
            if start_type == 'existing':
                # Existing codebase - path must exist
                template_source = "existing"
                selected_template = None
                framework = Framework.DEFAULT  # Will be detected or set later
                
            elif start_type == 'minimal':
                # Minimal project - use default/default
                template_source = "minimal"
                selected_template = "default/default"
                framework = Framework.DEFAULT
                
            elif start_type == 'template':
                # Template project - select framework and template from API
                console.print("\n[bold]Select framework:[/bold]\n")
                
                # TODO: Get frameworks from REST API
                selectable_frameworks = Framework.get_selectable_frameworks()
                
                framework_choices = []
                for fw in selectable_frameworks:
                    label = f"{fw.value} ({fw.category})"
                    framework_choices.append((label, fw))
                
                fw_questions = [
                    inquirer.List(
                        'framework',
                        message="Choose framework",
                        choices=framework_choices,
                        carousel=True
                    ),
                ]
                
                fw_answer = safe_prompt(fw_questions, "[dim]Initialization cancelled.[/dim]")
                if not fw_answer:
                    return
                
                framework = fw_answer['framework']
                
                # TODO: Get templates from REST API for selected framework
                console.print(f"\n[bold]Select template for {framework.value}:[/bold]")
                
                # For now, use default template
                selected_template = f"{framework.value}/default"
                template_source = "template"
        else:
            # Non-interactive mode
            if existing:
                template_source = "existing"
                selected_template = None
                framework = Framework.DEFAULT  # Will be detected or set later
            elif minimal:
                template_source = "minimal"
                selected_template = "default/default"
                framework = Framework.DEFAULT
            elif from_template:
                template_source = "template"
                selected_template = from_template
                # Extract framework from template name (e.g., "langchain/problem_solver")
                if "/" in from_template:
                    framework_name = from_template.split("/")[0]
                    try:
                        framework = Framework.from_string(framework_name)
                    except ValueError:
                        framework = Framework.DEFAULT
                else:
                    framework = Framework.DEFAULT
            else:
                # Default to template mode
                template_source = "template"
                selected_template = template
                framework = get_selected_framework(kwargs) or Framework.DEFAULT
        
        # Step 2: Get project details and path
        
        # For existing codebase, path handling is different
        if template_source == "existing":
            # For existing codebase, the path must exist
            # In non-interactive mode, use the provided path
            # In interactive mode, ask for the path first, then name/description
            if is_interactive:
                # Ask for path first (before name/description)
                path_input = Prompt.ask(
                    "[cyan]Project path[/cyan]",
                    default=str(project_path.resolve())
                )
                project_path = Path(path_input).resolve()
            
            # Check if path exists
            if not project_path.exists():
                raise click.ClickException(
                    f"Path does not exist: {project_path}\n"
                    "For existing codebase, the directory must already exist."
                )
            
            if not project_path.is_dir():
                raise click.ClickException(
                    f"Path is not a directory: {project_path}\n"
                    "For existing codebase, the path must be a directory."
                )
            
            # Check if it's already a RunAgent project
            config_path = project_path / AGENT_CONFIG_FILE_NAME
            if config_path.exists():
                raise click.ClickException(
                    f"RunAgent project already exists at {project_path}\n"
                    f"Found existing {AGENT_CONFIG_FILE_NAME} file.\n"
                    "This directory is already initialized as a RunAgent project."
                )
            
            # Set default name based on folder name
            is_custom_path = True
            suggested_name = project_path.name
            
        else:
            # For minimal/template projects, use existing logic
            is_custom_path = project_path.resolve() != Path.cwd()
        
        # Get name and description
        if is_interactive or not (name and description):
            console.print("\n[bold]Project Details:[/bold]\n")
            
            if template_source == "existing":
                suggested_name = project_path.name
            else:
                suggested_name = project_path.name if is_custom_path else "runagent-starter"
            
            agent_name = Prompt.ask(
                "[cyan]Agent name[/cyan]",
                default=suggested_name
            )
            
            agent_description = Prompt.ask(
                "[cyan]Agent description[/cyan]",
                default="My AI agent"
            )
        
        # Step 3: Get project path (if not already specified and not existing codebase)
        if template_source != "existing" and (is_interactive or not is_custom_path):
            custom_path = project_path / agent_name.lower().replace(" ", "-")
            suggested_path = project_path.resolve() if is_custom_path else custom_path
            path_input = Prompt.ask(
                "[cyan]Project path[/cyan]",
                default=suggested_path.as_posix()
            )
            project_path = Path(path_input).resolve()
        
        # Step 4: Get authentication type
        if is_interactive or not use_auth:
            console.print("\n[bold]Authentication:[/bold]\n")
            
            auth_questions = [
                inquirer.List(
                    'auth_type',
                    message="Select authentication type",
                    choices=[
                        ('None (no authentication)', 'none'),
                        ('API Key', 'api_key'),
                    ],
                    default=('None (no authentication)', 'none'),
                    carousel=True
                ),
            ]
            
            auth_answer = safe_prompt(auth_questions, "[dim]Initialization cancelled.[/dim]")
            if not auth_answer:
                return
            
            auth_type = auth_answer['auth_type']
        
        # Ensure the path exists (except for existing codebase which must already exist)
        if template_source != "existing":
            project_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Show configuration summary
        template_display = selected_template if selected_template else "N/A"
        console.print(Panel(
            f"[bold]Project Configuration:[/bold]\n\n"
            f"[dim]Name:[/dim] [cyan]{agent_name}[/cyan]\n"
            f"[dim]Description:[/dim] [white]{agent_description}[/white]\n"
            f"[dim]Source:[/dim] [magenta]{template_source}[/magenta]\n"
            f"[dim]Template:[/dim] [yellow]{template_display}[/yellow]\n"
            f"[dim]Framework:[/dim] [blue]{framework.value}[/blue]\n"
            f"[dim]Auth:[/dim] [green]{auth_type}[/green]\n"
            f"[dim]Path:[/dim] [blue]{project_path}[/blue]",
            title="[bold cyan]Creating Agent[/bold cyan]",
            border_style="cyan"
        ))
        
        # Initialize project based on source type
        success = False
        if template_source == "existing":
            # For existing codebase, just create the config file
            # No template download needed
            success = True  # We'll handle config creation below
        elif template_source == "minimal":
            # Initialize minimal project (formerly blank)
            success = sdk.init_project(
                folder_path=project_path,
                framework=framework.value,
                template="default",
                overwrite=overwrite
            )
        elif template_source == "template":
            # Initialize from template
            success = sdk.init_project(
                folder_path=project_path,
                framework=framework.value,
                template=selected_template.split("/")[1] if "/" in selected_template else "default",
                overwrite=overwrite
            )
        
        if not success and template_source != "existing":
            raise Exception("Project initialization failed")
        
        # Generate agent ID and create/update config file
        try:
            # Suppress Pydantic datetime warnings during config update
            warnings.filterwarnings('ignore', category=UserWarning, module='pydantic')
            
            # Generate unique agent ID
            agent_id = generate_agent_id()
            
            config_path = project_path / AGENT_CONFIG_FILE_NAME
            
            if template_source == "existing":
                # For existing codebase, create new config from scratch
                # Empty entrypoints list, but assign agent_id
                from runagent.utils.schema import AgentArchitecture
                
                # Create valid template_source for existing codebase
                template_source_obj = TemplateSource(
                    repo_url=TEMPLATE_REPO_URL,
                    author="runagent-cli",
                    path=str(project_path)
                )
                
                config = RunAgentConfig(
                    agent_name=agent_name,
                    description=agent_description,
                    framework=framework,
                    template="",  # Empty for existing codebase
                    version="1.0.0",
                    created_at=datetime.now(),
                    template_source=template_source_obj,
                    agent_architecture=AgentArchitecture(entrypoints=[]),  # Empty entrypoints list
                    env_vars={},
                    agent_id=agent_id,
                    auth_settings={"type": auth_type}
                )
                
                # Use model_dump() to get dict, then write directly
                config_dict = config.to_dict()
                
                # Write config file
                with open(config_path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
                
                console.print(f"\n[dim]✅ Generated agent ID: [cyan]{agent_id}[/cyan][/dim]")
                console.print("[dim]✅ Created RunAgent configuration file[/dim]")
                console.print(f"[dim]✅ Set authentication type: [green]{auth_type}[/green][/dim]")
                console.print("[yellow]⚠️  No entrypoints configured. Add entrypoints to runagent.config.json to enable agent execution.[/yellow]")
                
                # Create database entry for the initialized agent
                try:
                    # Load config with defaults
                    config_with_defaults = get_agent_config_with_defaults(project_path)
                    
                    # Generate config fingerprint
                    config_fingerprint = generate_config_fingerprint(project_path)
                    
                    # Create database service and add agent
                    db_service = DBService()
                    
                    # Get active project ID from user metadata
                    active_project_id = db_service.get_active_project_id()
                    
                    result = db_service.add_agent(
                        agent_id=agent_id,
                        agent_path=str(project_path),
                        host="",  # Will be updated when deployed
                        port=0000,  # Will be updated when deployed
                        framework=framework.value,
                        status="initialized",  # New status for initialized agents
                        agent_name=config_with_defaults.get('agent_name'),
                        description=config_with_defaults.get('description'),
                        template=config_with_defaults.get('template'),
                        version=config_with_defaults.get('version'),
                        initialized_at=config_with_defaults.get('created_at'),
                        config_fingerprint=config_fingerprint,
                        project_id=active_project_id,  # Get from user metadata, not config
                    )
                    
                    if result.get('success'):
                        console.print("[dim]✅ Agent registered in database[/dim]")
                    else:
                        console.print(f"[yellow]Could not register agent in database: {result.get('error', 'Unknown error')}[/yellow]")
                        
                except Exception as db_error:
                    console.print(f"[yellow]Could not register agent in database: {db_error}[/yellow]")
                
            elif config_path.exists():
                # Load config using the schema (handles missing fields gracefully)
                config = get_agent_config(project_path)
                
                # Update config with user-provided values and agent_id
                config.agent_id = agent_id
                config.agent_name = agent_name
                config.description = agent_description
                
                # Add auth_settings
                config_dict = config.to_dict()
                config_dict['auth_settings'] = {
                    'type': auth_type
                }
                
                # Save updated config
                with open(config_path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
                
                console.print(f"\n[dim]✅ Generated agent ID: [cyan]{agent_id}[/cyan][/dim]")
                console.print("[dim]✅ Updated agent name and description in config[/dim]")
                console.print(f"[dim]✅ Set authentication type: [green]{auth_type}[/green][/dim]")
                
                # Create database entry for the initialized agent
                try:
                    # Load config with defaults
                    config_with_defaults = get_agent_config_with_defaults(project_path)
                    
                    # Generate config fingerprint
                    config_fingerprint = generate_config_fingerprint(project_path)
                    
                    # Create database service and add agent
                    db_service = DBService()
                    
                    # Get active project ID from user metadata
                    active_project_id = db_service.get_active_project_id()
                    
                    result = db_service.add_agent(
                        agent_id=agent_id,
                        agent_path=str(project_path),
                        host="",  # Will be updated when deployed
                        port=0000,  # Will be updated when deployed
                        framework=framework.value,
                        status="initialized",  # New status for initialized agents
                        agent_name=config_with_defaults.get('agent_name'),
                        description=config_with_defaults.get('description'),
                        template=config_with_defaults.get('template'),
                        version=config_with_defaults.get('version'),
                        initialized_at=config_with_defaults.get('created_at'),
                        config_fingerprint=config_fingerprint,
                        project_id=active_project_id,  # Get from user metadata, not config
                    )
                    
                    if result.get('success'):
                        console.print("[dim]✅ Agent registered in database[/dim]")
                    else:
                        console.print(f"[yellow]Could not register agent in database: {result.get('error', 'Unknown error')}[/yellow]")
                        
                except Exception as db_error:
                    console.print(f"[yellow]Could not register agent in database: {db_error}[/yellow]")
                    
        except Exception as e:
            console.print(f"[yellow]Could not update config: {e}[/yellow]")
        
        # Success message
        relative_path = project_path.relative_to(Path.cwd()) if project_path != Path.cwd() else Path(".")
        
        console.print(Panel(
            f"[bold green]✅ Agent '{agent_name}' created successfully![/bold green]\n\n"
            f"[dim]Location:[/dim] [cyan]{relative_path}[/cyan]\n"
            f"[dim]Framework:[/dim] [magenta]{framework.value}[/magenta]\n"
            f"[dim]Source:[/dim] [blue]{template_source}[/blue]\n"
            f"[dim]Auth:[/dim] [green]{auth_type}[/green]",
            title="[bold green]Success[/bold green]",
            border_style="green"
        ))
        
        # Simple next steps
        console.print("\n[bold]Next Steps:[/bold]")
        if relative_path != Path("."):
            path_str = str(relative_path)
            console.print(f"   1. [cyan]cd {path_str}[/cyan]")
            console.print(f"   2. Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")
            console.print(f"   3. Serve locally: [cyan]runagent serve .[/cyan]")
            console.print(
                f"      (or run [cyan]runagent serve {path_str}[/cyan] from the current directory)"
            )
        else:
            console.print(f"   1. Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")
            console.print(f"   2. Serve locally: [cyan]runagent serve .[/cyan]")
    
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
        folder_path = str(e).split("'")[1] if "'" in str(e) else str(e)
        
        console.print(Panel(
            f"[bold yellow]Directory Already Exists[/bold yellow]\n\n"
            f"[dim]Path:[/dim] [cyan]{folder_path}[/cyan]\n\n"
            f"The directory already exists and is not empty.\n\n"
            f"[bold]Options:[/bold]\n"
            f"  • Use [cyan]--overwrite[/cyan] flag to replace existing files\n"
            f"  • Remove the directory manually",
            title="[bold yellow]Path Conflict[/bold yellow]",
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
