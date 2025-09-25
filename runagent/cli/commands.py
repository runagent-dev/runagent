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
            user_info = config_status.get('user_info', {})
            if user_info.get('email'):
                console.print(f"   User: [green]{user_info.get('email')}[/green]")

            if not click.confirm("Do you want to reconfigure?"):
                return

        console.print("🔑 [cyan]Setting up RunAgent authentication...[/cyan]")

        # Configure SDK with validation
        try:
            sdk.configure(api_key=api_key, base_url=base_url, save=True)
            console.print("✅ [green]Setup completed successfully![/green]")
        except AuthenticationError as auth_err:
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
                console.print(f"   • Trying to connect to: {base_url or sdk.config.base_url}")
            else:
                console.print("   • Check your API key and network connection")
                console.print("   • Contact support if the issue persists")
            
            raise click.ClickException("Authentication failed")

        # Show user information (from cached data)
        config_status = sdk.get_config_status()
        user_info = config_status.get('user_info', {})
        
        if user_info and user_info.get('email'):
            console.print("\n👤 [bold]User Information:[/bold]")
            console.print(f"   Email: [cyan]{user_info.get('email')}[/cyan]")
            if user_info.get('user_id'):
                console.print(f"   User ID: [dim]{user_info.get('user_id')}[/dim]")
            if user_info.get('tier'):
                console.print(f"   Tier: [yellow]{user_info.get('tier')}[/yellow]")

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

        # Show next steps
        console.print("\n💡 [bold]Next Steps:[/bold]")
        console.print("   • Test with a local agent: [cyan]runagent serve <path>[/cyan]")
        console.print("   • Check middleware sync: [cyan]runagent local-sync --status[/cyan]")
        console.print("   • Upload agent to middleware: [cyan]runagent upload --folder <path>[/cyan]")

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
@add_framework_options  # This automatically adds all framework options!
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
def init(template, interactive, overwrite, path, **kwargs):
    """Initialize a new RunAgent project"""
    
    try:
        sdk = RunAgent()
        
        # Extract selected framework using our helper
        selected_framework = get_selected_framework(kwargs)
        framework = selected_framework if selected_framework else Framework.DEFAULT
        
        if interactive:
            if framework == Framework.DEFAULT:
                console.print("🎯 [bold]Available frameworks:[/bold]")
                selectable_frameworks = Framework.get_selectable_frameworks()
                
                for i, fw in enumerate(selectable_frameworks, 1):
                    category_emoji = "🐍" if fw.is_pythonic() else "🌐" if fw.is_webhook() else "❓"
                    console.print(f"  {i}. {category_emoji} {fw.value} ({fw.category})")
                
                choice = click.prompt(
                    "Select framework", 
                    type=click.IntRange(1, len(selectable_frameworks)), 
                    default=1
                )
                framework = selectable_frameworks[choice - 1]
            
            if template == "default":
                templates = sdk.list_templates(framework.value)
                template_list = templates.get(framework.value, ["default"])
                
                console.print(f"\n🧱 [bold]Available templates for {framework.value}:[/bold]")
                for i, tmpl in enumerate(template_list, 1):
                    console.print(f"  {i}. {tmpl}")
                
                choice = click.prompt(
                    "Select template", 
                    type=click.IntRange(1, len(template_list)), 
                    default=1
                )
                template = template_list[choice - 1]
            
            if path.resolve() == Path.cwd():
                project_name = click.prompt(
                    "Enter project name",
                    type=str,
                    default="runagent-project"
                )
                path = Path.cwd() / project_name
        
        # Validate framework if it came from string input
        if isinstance(framework, str):
            try:
                framework = Framework.from_string(framework)
            except ValueError as e:
                raise click.UsageError(str(e))
        
        # Use the path as the project location
        project_path = path.resolve()
        relative_project_path = project_path.relative_to(Path.cwd())
        
        # Ensure the path exists
        project_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Show configuration with enhanced formatting
        console.print(f"\n🚀 [bold]Initializing project:[/bold]")
        console.print(f"   Path: [cyan]{relative_project_path}[/cyan]")
        
        # Enhanced framework display with category
        framework_display = framework.value
        if not framework.is_default():
            category_emoji = "🐍" if framework.is_pythonic() else "🌐" if framework.is_webhook() else "❓"
            framework_display = f"{category_emoji} {framework.value} ({framework.category})"
        
        console.print(f"   Framework: [magenta]{framework_display}[/magenta]")
        console.print(f"   Template: [yellow]{template}[/yellow]")
        
        # Initialize project
        success = sdk.init_project(
            folder_path=project_path,
            framework=framework.value,  # Pass the string value
            template=template,
            overwrite=overwrite
        )
        
        if success:
            console.print(f"\n✅ [green]Project initialized successfully![/green]")
            console.print(f"📁 Created at: [cyan]{relative_project_path}[/cyan]")
            
            # Enhanced next steps with framework-specific guidance
            console.print("\n📝 [bold]Next steps:[/bold]")
            console.print(f"  1. [cyan]cd {relative_project_path}[/cyan]")
            console.print(f"  2. Update your API keys in [yellow].env[/yellow] file")
            
            # Framework-specific guidance
            if framework.is_pythonic():
                console.print(f"  3. Install dependencies: [cyan]pip install -r requirements.txt[/cyan]")
                console.print(f"  4. Deploy locally: [cyan]runagent serve {relative_project_path}[/cyan]")
            elif framework.is_webhook():
                console.print(f"  3. Configure webhook endpoints in your workflow")
                console.print(f"  4. Deploy locally: [cyan]runagent serve {relative_project_path}[/cyan]")
            else:
                console.print(f"  3. Deploy locally: [cyan]runagent serve {relative_project_path}[/cyan]")
            
            console.print(
                f"  5. Test: [cyan]Test the agent with any of our SDKs. For more details, refer to: [link]https://docs.run-agent.ai/sdk/overview[/link][/cyan]"
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


# @click.command()
# @click.option("--folder", required=True, help="Folder containing agent files")
# @click.option("--framework", help="Framework type (auto-detected if not specified)")
# @click.option("--replace", help="Agent ID to replace (for capacity management)")
# @click.option("--port", type=int, help="Preferred port (auto-allocated if unavailable)")
# @click.option("--host", default="127.0.0.1", help="Preferred host")
# def deploy_local(folder, framework, replace, port, host):
#     """Deploy agent locally for testing with automatic port allocation"""

#     try:
#         sdk = RunAgent()

#         # Validate folder
#         if not Path(folder).exists():
#             raise click.ClickException(f"Folder not found: {folder}")

#         console.print(f"🚀 [bold]Deploying agent locally with auto port allocation...[/bold]")
#         console.print(f"📁 Source: [cyan]{folder}[/cyan]")

#         if replace:
#             # Replace existing agent
#             result = sdk.db_service.replace_agent(
#                 old_agent_id=replace,
#                 new_agent_id=str(uuid.uuid4()),  # Generate new ID
#                 agent_path=folder,
#                 host=host,
#                 port=port,
#                 framework=framework or detect_framework(folder),
#             )
#         else:
#             # Add new agent with auto port allocation
#             import uuid
#             agent_id = str(uuid.uuid4())
#             result = sdk.db_service.add_agent_with_auto_port(
#                 agent_id=agent_id,
#                 agent_path=folder,
#                 framework=framework or detect_framework(folder),
#                 status="deployed",
#                 preferred_host=host,
#                 preferred_port=port,
#             )

#         if result.get("success"):
#             agent_id = result.get("new_agent_id") if replace else result.get("agent_id")
#             allocated_host = result.get("allocated_host", host)
#             allocated_port = result.get("allocated_port", port)
            
#             console.print(f"\n✅ [green]Local deployment successful![/green]")
#             console.print(f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]")
#             console.print(f"🔌 Allocated Address: [bold blue]{allocated_host}:{allocated_port}[/bold blue]")
#             console.print(f"🌐 Endpoint: [link]http://{allocated_host}:{allocated_port}[/link]")

#             if replace:
#                 console.print(f"🔄 Replaced agent: [yellow]{replace}[/yellow]")

#             # Show capacity info
#             # capacity = sdk.get_local_capacity()
#             capacity_info = sdk.db_service.get_database_capacity_info()

#             console.print(
#                 f"📊 Capacity: [cyan]{capacity.get('current_count', 1)}/5[/cyan] slots used"
#             )

#             console.print(f"\n💡 [bold]Next steps:[/bold]")
#             console.print(f"  • Start server: [cyan]runagent serve {folder}[/cyan]")
#             console.print(f"  • Test agent: [cyan]runagent run --id {agent_id} --local[/cyan]")
#             console.print(f"  • Or use Python SDK:")
#             console.print(f"    [dim]from runagent import RunAgentClient[/dim]")
#             console.print(f"    [dim]client = RunAgentClient(agent_id='{agent_id}', local=True)[/dim]")
#         else:
#             error_code = result.get("error_code")
#             if error_code == "DATABASE_FULL":
#                 capacity_info = result.get("capacity_info", {})
#                 console.print(f"\n❌ [red]Database at full capacity![/red]")
#                 console.print(
#                     f"📊 Current: {capacity_info.get('current_count', 0)}/5 agents"
#                 )

#                 oldest_agent = capacity_info.get("oldest_agent", {}).get("agent_id")
#                 if oldest_agent:
#                     console.print(f"\n💡 [yellow]Suggested command:[/yellow]")
#                     console.print(
#                         f"[cyan]runagent deploy-local --folder {folder} --replace {oldest_agent}[/cyan]"
#                     )

#                 raise click.ClickException(result.get("error"))
#             else:
#                 raise click.ClickException(result.get("error"))

#     except ValidationError as e:
#         console.print(f"❌ [red]Validation error:[/red] {e}")
#         raise click.ClickException("Deployment failed")
#     except Exception as e:
#         console.print(f"❌ [red]Deployment error:[/red] {e}")
#         raise click.ClickException("Deployment failed")

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
def upload(path):
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
        if not Path(path).exists():
            raise click.ClickException(f"Folder not found: {path}")

        console.print(f"📤 [bold]Uploading agent...[/bold]")
        console.print(f"📁 Source: [cyan]{path}[/cyan]")

        # Upload agent (framework auto-detected)
        result = sdk.upload_agent(folder=str(path))

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
            from runagent.utils.agent_id import generate_agent_id
            new_agent_id = generate_agent_id()
            
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
        raise click.ClickException(f"Execution failed: {e}")


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


@click.command()
@click.option("--status", is_flag=True, help="Show sync status")
@click.option("--test", is_flag=True, help="Test middleware connection")
def local_sync(status, test):
    """Manage local agent sync with middleware - ENHANCED"""
    try:
        sdk = RunAgent()
        
        if not sdk.config.is_configured():
            console.print("❌ [red]RunAgent not configured[/red]")
            console.print("💡 Run: [cyan]runagent setup --api-key <your-key>[/cyan]")
            raise click.ClickException("Setup required")
        
        from runagent.sdk.deployment.middleware_sync import MiddlewareSyncService
        sync_service = MiddlewareSyncService(sdk.config)
        
        if status or (not test):
            # Show detailed sync status
            console.print("\n📡 [bold]Middleware Sync Status[/bold]")
            console.print("=" * 40)
            
            # API Key status
            if sync_service.api_key:
                console.print("🔑 [green]API Key: CONFIGURED[/green]")
                console.print(f"   Key: [dim]{sync_service.api_key[:16]}...[/dim]")
            else:
                console.print("🔑 [red]API Key: NOT CONFIGURED[/red]")
            
            # Base URL
            console.print(f"🌐 Base URL: [blue]{sync_service.config.base_url}[/blue]")
            
            # Authentication status
            if sync_service.auth_validated:
                console.print("🔐 [green]Authentication: VALID[/green]")
            else:
                console.print("🔐 [red]Authentication: INVALID[/red]")
            
            # Overall sync status
            if sync_service.sync_enabled:
                console.print("✅ [green]Sync Status: ENABLED[/green]")
                console.print(" Local agent runs will sync to middleware")
            else:
                console.print("❌ [red]Sync Status: DISABLED[/red]")
                console.print("⚠️ Local agents will only be stored locally")
            
            if not sync_service.sync_enabled:
                console.print("\n [yellow]To enable sync:[/yellow]")
                console.print("   1. Get API key from middleware dashboard")
                console.print("   2. Run: [cyan]runagent setup --api-key <your-key>[/cyan]")
        
        if test:
            console.print("\n [bold]Testing Connection...[/bold]")
            
            if not sync_service.api_key:
                console.print("❌ [red]No API key configured[/red]")
                raise click.ClickException("API key required for testing")
            
            # Test basic connection
            console.print("1. Testing basic connectivity...")
            connection_result = sync_service._test_middleware_connection()
            if connection_result:
                console.print("   ✅ [green]Basic connection: SUCCESS[/green]")
            else:
                console.print("   ❌ [red]Basic connection: FAILED[/red]")
                raise click.ClickException("Cannot connect to middleware")
            
            # Test authentication
            console.print("2. Testing authentication...")
            auth_result = sync_service._test_supabase_authentication()
            if auth_result:
                console.print("   ✅ [green]Authentication: SUCCESS[/green]")
            else:
                console.print("   ❌ [red]Authentication: FAILED[/red]")
                console.print("    Check your API key")
                raise click.ClickException("Authentication failed")
            
            # Test user info endpoint
            console.print("3. Testing user info endpoint...")
            try:
                response = sync_service.rest_client.http.get("/users/auth-user-info", timeout=10)
                if response.status_code == 200:
                    user_data = response.json()
                    user_info = user_data.get("user", {})
                    console.print("   ✅ [green]User info: SUCCESS[/green]")
                    console.print(f"   👤 Email: [cyan]{user_info.get('email', 'Unknown')}[/cyan]")
                    if user_info.get('id'):
                        console.print(f"   🆔 User ID: [dim]{user_info.get('id')}[/dim]")
                else:
                    console.print(f"   ❌ [red]User info: FAILED (HTTP {response.status_code})[/red]")
            except Exception as e:
                console.print(f"   ❌ [red]User info: ERROR ({e})[/red]")
            
            console.print("\n✅ [bold green]All tests passed! Middleware sync is working.[/bold green]")
    
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Local sync error: {e}[/red]")
        raise click.ClickException("Local sync command failed")


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