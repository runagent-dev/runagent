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

console = Console()


@click.command()
@click.option("--api-key", required=True, help="Your API key")
@click.option("--base-url", help="API base URL")
@click.option("--force", is_flag=True, help="Force reconfiguration")
def setup(api_key, base_url, force):
    """Setup RunAgent authentication"""
    try:
        sdk = RunAgent()

        # Check if already configured
        if sdk.is_configured() and not force:
            config_status = sdk.get_config_status()
            console.print("⚠️ RunAgent is already configured:")
            console.print(f"   Base URL: [blue]{config_status.get('base_url')}[/blue]")
            console.print(
                f"   User: [green]{config_status.get('user_info', {}).get('email', 'Unknown')}[/green]"
            )

            if not click.confirm("Do you want to reconfigure?"):
                return

        # Configure SDK
        sdk.configure(api_key=api_key, base_url=base_url, save=True)

        console.print("✅ [green]Setup completed successfully![/green]")

        # Show user info
        config_status = sdk.get_config_status()
        user_info = config_status.get("user_info", {})
        if user_info:
            console.print("\n👤 [bold]User Information:[/bold]")
            for key, value in user_info.items():
                console.print(f"   {key}: [cyan]{value}[/cyan]")

    except AuthenticationError as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Authentication failed:[/red] {e}")
        raise click.ClickException("Setup failed")
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Setup error:[/red] {e}")
        raise click.ClickException("Setup failed")


@click.command()
@click.option("--yes", is_flag=True, help="Skip confirmation")
def teardown(yes):
    """Remove RunAgent configuration"""
    try:
        sdk = RunAgent()

        if not yes:
            config_status = sdk.get_config_status()
            if config_status.get("configured"):
                console.print("📋 [bold]Current configuration:[/bold]")
                console.print(
                    f"   Base URL: [blue]{config_status.get('base_url')}[/blue]"
                )
                user_info = config_status.get("user_info", {})
                if user_info.get("email"):
                    console.print(f"   User: [green]{user_info.get('email')}[/green]")

            if not click.confirm(
                "⚠️ This will remove all RunAgent configuration. Continue?"
            ):
                console.print("Teardown cancelled.")
                return

        # Clear configuration
        sdk.config.clear()

        console.print("✅ [green]RunAgent teardown completed successfully![/green]")
        console.print(
            "💡 Run [cyan]'runagent setup --api-key <key>'[/cyan] to reconfigure"
        )

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Teardown error:[/red] {e}")
        raise click.ClickException("Teardown failed")


@click.command()
@click.option("--id", "agent_id", required=True, help="Agent ID to delete")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def delete(agent_id, yes):
    """Delete an agent from the local database"""
    try:
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
            console.print(f"❌ [red]Failed to delete agent: {result.get('error')}[/red]")
            raise click.ClickException("Deletion failed")
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Delete error:[/red] {e}")
        raise click.ClickException("Delete failed")





@click.command()
@click.option("--template", default="default", help="Template variant (basic, advanced, default)")
@click.option("--interactive", "-i", is_flag=True, help="Enable interactive prompts")
@click.option("--overwrite", is_flag=True, help="Overwrite existing folder")
@click.option("--langchain", is_flag=True, help="Use LangChain framework")
@click.option("--langgraph", is_flag=True, help="Use LangGraph framework")
@click.option("--llamaindex", is_flag=True, help="Use LlamaIndex framework")
@click.argument(
    "path",
    type=click.Path(
        file_okay=False,  # Don't allow files
        dir_okay=True,  # Allow directories only
        readable=True,  # Must be readable
        resolve_path=True,  # Convert to absolute path
        path_type=Path,  # Return as pathlib.Path object
    ),
    default=".",
    required=False,  # Make path optional
)
def init(template, interactive, overwrite, langchain, langgraph, llamaindex, path):
    """Initialize a new RunAgent project"""

    try:
        sdk = RunAgent()

        # Check for mutually exclusive framework flags
        framework_flags = [langchain, langgraph, llamaindex]
        framework_str = ["langchain", "langgraph", "llamaindex"]
        
        if sum(framework_flags) > 1:
            frameworks_str = ", ".join(f"--{fw}" for fw in framework_str)
            raise click.UsageError(f"Only one framework can be specified: {frameworks_str}")

        framework = (
            [name for name, flag in zip(framework_str, framework_flags) if flag] or ["default"]
        )[0]
        
        if interactive:
            if framework == "default":
                console.print("🎯 [bold]Available frameworks:[/bold]")
                for i, fw in enumerate(framework_str, 1):    # need to start from 1
                    console.print(f"  {i}. {fw}")

                choice = click.prompt(
                    "Select framework", type=click.IntRange(1, len(framework_str)), default=1
                )
                framework = framework_str[choice - 1]

            if template == "default":
                templates = sdk.list_templates(framework)
                template_list = templates.get(framework, ["default"])

                console.print(f"\n🧱 [bold]Available templates for {framework}:[/bold]")
                for i, tmpl in enumerate(template_list, 1):
                    console.print(f"  {i}. {tmpl}")

                choice = click.prompt(
                    "Select template", type=click.IntRange(1, len(template_list)), default=1
                )
                template = template_list[choice - 1]
                
            if path.resolve() == Path.cwd():
                project_name = click.prompt(
                    "Enter project name",
                    type=str,
                    default="runagent-project"
                )
                # Update path to include project name
                path = Path.cwd() / project_name

        # Use the path as the project location
        project_path = path.resolve()
        relative_project_path = project_path.relative_to(Path.cwd())
        
        # Ensure the path exists (create parent directories if needed)
        project_path.parent.mkdir(parents=True, exist_ok=True)

        # Show configuration
        console.print(f"\n🚀 [bold]Initializing project:[/bold]")

        console.print(f"   Path: [cyan]{relative_project_path}[/cyan]")
        console.print(f"   Framework: [magenta]{framework if framework else 'None'}[/magenta]")
        console.print(f"   Template: [yellow]{template}[/yellow]")

        # Initialize project
        success = sdk.init_project(
            folder_path=project_path,
            framework=framework,
            template=template,
            overwrite=overwrite
        )

        if success:
            console.print(f"\n✅ [green]Project initialized successfully![/green]")
            console.print(f"📁 Created at: [cyan]{relative_project_path}[/cyan]")

            # Show next steps
            console.print("\n📝 [bold]Next steps:[/bold]")
            console.print(f"  1. [cyan]cd {relative_project_path}[/cyan]")
            console.print(f"  2. Update your API keys in [yellow].env[/yellow] file")
            console.print(f"  3. Deploy locally: [cyan]runagent serve {relative_project_path}[/cyan]")
            console.print(
                f"  4. Test: [cyan]Test the agent with any of our SDKs. For more details, refer to: [link]https://docs.run-agent.ai/sdk/overview[/link][/cyan]"
            )

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
        console.print(f"❌ [red]Template error:[/red] {e}")
        raise click.ClickException("Template operation failed")


@click.command()
@click.option("--folder", required=True, help="Folder containing agent files")
@click.option("--framework", help="Framework type (auto-detected if not specified)")
@click.option("--replace", help="Agent ID to replace (for capacity management)")
@click.option("--port", type=int, help="Preferred port (auto-allocated if unavailable)")
@click.option("--host", default="127.0.0.1", help="Preferred host")
def deploy_local(folder, framework, replace, port, host):
    """Deploy agent locally for testing with automatic port allocation"""

    try:
        sdk = RunAgent()

        # Validate folder
        if not Path(folder).exists():
            raise click.ClickException(f"Folder not found: {folder}")

        console.print(f"🚀 [bold]Deploying agent locally with auto port allocation...[/bold]")
        console.print(f"📁 Source: [cyan]{folder}[/cyan]")

        if replace:
            # Replace existing agent
            result = sdk.db_service.replace_agent(
                old_agent_id=replace,
                new_agent_id=str(uuid.uuid4()),  # Generate new ID
                agent_path=folder,
                host=host,
                port=port,
                framework=framework or detect_framework(folder),
            )
        else:
            # Add new agent with auto port allocation
            import uuid
            agent_id = str(uuid.uuid4())
            result = sdk.db_service.add_agent_with_auto_port(
                agent_id=agent_id,
                agent_path=folder,
                framework=framework or detect_framework(folder),
                status="deployed",
                preferred_host=host,
                preferred_port=port,
            )

        if result.get("success"):
            agent_id = result.get("new_agent_id") if replace else result.get("agent_id")
            allocated_host = result.get("allocated_host", host)
            allocated_port = result.get("allocated_port", port)
            
            console.print(f"\n✅ [green]Local deployment successful![/green]")
            console.print(f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]")
            console.print(f"🔌 Allocated Address: [bold blue]{allocated_host}:{allocated_port}[/bold blue]")
            console.print(f"🌐 Endpoint: [link]http://{allocated_host}:{allocated_port}[/link]")

            if replace:
                console.print(f"🔄 Replaced agent: [yellow]{replace}[/yellow]")

            # Show capacity info
            # capacity = sdk.get_local_capacity()
            capacity_info = sdk.db_service.get_database_capacity_info()

            console.print(
                f"📊 Capacity: [cyan]{capacity.get('current_count', 1)}/5[/cyan] slots used"
            )

            console.print(f"\n💡 [bold]Next steps:[/bold]")
            console.print(f"  • Start server: [cyan]runagent serve {folder}[/cyan]")
            console.print(f"  • Test agent: [cyan]runagent run --id {agent_id} --local[/cyan]")
            console.print(f"  • Or use Python SDK:")
            console.print(f"    [dim]from runagent import RunAgentClient[/dim]")
            console.print(f"    [dim]client = RunAgentClient(agent_id='{agent_id}', local=True)[/dim]")
        else:
            error_code = result.get("error_code")
            if error_code == "DATABASE_FULL":
                capacity_info = result.get("capacity_info", {})
                console.print(f"\n❌ [red]Database at full capacity![/red]")
                console.print(
                    f"📊 Current: {capacity_info.get('current_count', 0)}/5 agents"
                )

                oldest_agent = capacity_info.get("oldest_agent", {}).get("agent_id")
                if oldest_agent:
                    console.print(f"\n💡 [yellow]Suggested command:[/yellow]")
                    console.print(
                        f"[cyan]runagent deploy-local --folder {folder} --replace {oldest_agent}[/cyan]"
                    )

                raise click.ClickException(result.get("error"))
            else:
                raise click.ClickException(result.get("error"))

    except ValidationError as e:
        console.print(f"❌ [red]Validation error:[/red] {e}")
        raise click.ClickException("Deployment failed")
    except Exception as e:
        console.print(f"❌ [red]Deployment error:[/red] {e}")
        raise click.ClickException("Deployment failed")

@click.command()
@click.option("--folder", required=True, help="Folder containing agent files")
@click.option("--framework", help="Framework type (auto-detected if not specified)")
def upload(folder, framework):
    """Upload agent to remote server"""

    try:
        sdk = RunAgent()

        # Check authentication
        if not sdk.is_configured():
            console.print(
                "❌ [red]Not authenticated.[/red] Run [cyan]'runagent setup --api-key <key>'[/cyan] first"
            )
            raise click.ClickException("Authentication required")

        # Validate folder
        if not Path(folder).exists():
            raise click.ClickException(f"Folder not found: {folder}")

        console.print(f"📤 [bold]Uploading agent...[/bold]")
        console.print(f"📁 Source: [cyan]{folder}[/cyan]")

        # Upload agent
        result = sdk.upload_agent(folder=folder, framework=framework)

        if result.get("success"):
            agent_id = result["agent_id"]
            console.print(f"\n✅ [green]Upload successful![/green]")
            console.print(f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]")
            console.print(f"\n💡 [bold]Next step:[/bold]")
            console.print(f"[cyan]runagent start --id {agent_id}[/cyan]")
        else:
            raise click.ClickException(result.get("error"))

    except AuthenticationError as e:
        console.print(f"❌ [red]Authentication error:[/red] {e}")
        raise click.ClickException("Upload failed")
    except Exception as e:
        console.print(f"❌ [red]Upload error:[/red] {e}")
        raise click.ClickException("Upload failed")


@click.command()
@click.option("--id", "agent_id", required=True, help="Agent ID to start")
@click.option("--config", help="JSON configuration for deployment")
def start(agent_id, config):
    """Start an uploaded agent on remote server"""

    try:
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
            raise click.ClickException(result.get("error"))

    except AuthenticationError as e:
        console.print(f"❌ [red]Authentication error:[/red] {e}")
        raise click.ClickException("Start failed")
    except Exception as e:
        console.print(f"❌ [red]Start error:[/red] {e}")
        raise click.ClickException("Start failed")


@click.command()
@click.option("--folder", help="Folder containing agent files (for upload + start)")
@click.option("--id", "agent_id", help="Agent ID (for start only)")
@click.option("--local", is_flag=True, help="Deploy locally instead of remote server")
@click.option("--framework", help="Framework type (auto-detected if not specified)")
@click.option("--config", help="JSON configuration for deployment")
def deploy(folder, agent_id, local, framework, config):
    """Deploy agent (upload + start) or deploy locally"""

    try:
        sdk = RunAgent()

        if local:
            # Local deployment
            if not folder:
                raise click.ClickException("--folder is required for local deployment")

            # Use deploy_local command logic
            ctx = click.get_current_context()
            ctx.invoke(deploy_local, folder=folder, framework=framework)
            return

        # Remote deployment
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

        if folder:
            # Full deployment (upload + start)
            if not Path(folder).exists():
                raise click.ClickException(f"Folder not found: {folder}")

            console.print(f"🎯 [bold]Full deployment (upload + start)...[/bold]")
            console.print(f"📁 Source: [cyan]{folder}[/cyan]")

            result = sdk.deploy_remote(
                folder=folder, framework=framework, config=config_dict
            )

            if result.get("success"):
                console.print(f"\n✅ [green]Full deployment successful![/green]")
                console.print(
                    f"🆔 Agent ID: [bold magenta]{result.get('agent_id')}[/bold magenta]"
                )
                console.print(f"🌐 Endpoint: [link]{result.get('endpoint')}[/link]")
            else:
                raise click.ClickException(result.get("error"))

        elif agent_id:
            # Start existing agent
            ctx = click.get_current_context()
            ctx.invoke(start, agent_id=agent_id, config=config)

        else:
            raise click.ClickException(
                "Either --folder (for upload+start) or --id (for start only) is required"
            )

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Deployment error:[/red] {e}")
        raise click.ClickException("Deployment failed")



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
                framework=detect_framework(path),
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
        
        # Generic streaming mode with extra params
        runagent run --agent-id my-agent --generic-stream --debug=true --retries=3
    """
    
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
    # # VALIDATION 2: Generic mode selection
    # # ============================================
    # if generic and generic_stream:
    #     raise click.UsageError(
    #         "Cannot specify both --generic and --generic-stream. Choose one."
    #     )
    
    # # Default to generic mode if neither specified
    # if not generic and not generic_stream:
    #     generic = True
    #     console.print("🔧 Defaulting to --generic mode")
    
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
        raise click.ClickException(f"Execution failed: {e}")


@click.command()
@click.option("--cleanup-days", type=int, help="Clean up records older than N days")
@click.option("--agent-id", help="Show detailed info for specific agent")
@click.option("--capacity", is_flag=True, help="Show detailed capacity information")
def db_status(cleanup_days, agent_id, capacity):
    """Show local database status and statistics"""

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
                table.add_column("Agent ID", style="magenta", width=20)
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
                        agent['agent_id'][:18] + "...",
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
            # ... (keep existing agent_id specific logic unchanged)
            result = sdk.get_agent_info(agent_id, local=True)
            # ... rest of the existing code for this section
            return

        # Show general database stats
        stats = sdk.db_service.get_database_stats()
        capacity_info = sdk.db_service.get_database_capacity_info()

        console.print("\n📊 [bold]Local Database Status[/bold]")

        current_count = capacity_info.get("current_count", 0)
        is_full = capacity_info.get("is_full", False)
        status = "FULL" if is_full else "OK"
        console.print(
            f"Capacity: [cyan]{current_count}/5[/cyan] agents ([red]{status}[/red])"
            if is_full
            else f"Capacity: [cyan]{current_count}/5[/cyan] agents ([green]{status}[/green])"
        )

        console.print(f"Total Runs: [cyan]{stats.get('total_runs', 0)}[/cyan]")
        console.print(
            f"Database Size: [yellow]{stats.get('database_size_mb', 0)} MB[/yellow]"
        )
        console.print(
            f"Database Path: [blue]{stats.get('database_path', 'Unknown')}[/blue]"
        )

        # Show agent status breakdown
        status_counts = stats.get("agent_status_counts", {})
        if status_counts:
            console.print("\n📈 [bold]Agent Status Breakdown:[/bold]")
            for status, count in status_counts.items():
                console.print(f"  [cyan]{status}[/cyan]: {count}")

        # CHANGED: List agents in table format instead of simple list
        agents = sdk.db_service.list_agents()

        if agents:
            console.print(f"\n📋 [bold]Deployed Agents:[/bold]")
            
            # Create table for better formatting
            table = Table(title=f"Local Agents ({len(agents)} total)")
            table.add_column("Status", width=8)
            table.add_column("Files", width=6)
            table.add_column("Agent ID", style="magenta", width=20)
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
                    agent['agent_id'][:18] + "...",
                    agent['framework'],
                    f"{agent.get('host', 'N/A')}:{agent.get('port', 'N/A')}",
                    str(agent.get('run_count', 0)),
                    agent['status']
                )
            
            console.print(table)

            console.print(f"\n💡 Use [cyan]--agent-id <id>[/cyan] for detailed info")
            console.print(
                f"💡 Use [cyan]--capacity[/cyan] for capacity management info"
            )

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