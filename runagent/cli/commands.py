"""
CLI commands that use the restructured SDK internally.
"""

import json

# import requests
from pathlib import Path

import click
from rich.console import Console

# Import the new SDK
from runagent import RunAgent
from runagent.sdk.exceptions import (  # RunAgentError,; ConnectionError
    AuthenticationError,
    TemplateError,
    ValidationError,
)
from runagent.client.client import RunAgentClient

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
        console.print(f"❌ [red]Authentication failed:[/red] {e}")
        raise click.ClickException("Setup failed")
    except Exception as e:
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
        console.print(f"❌ [red]Teardown error:[/red] {e}")
        raise click.ClickException("Teardown failed")


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
        flags_set = sum(framework_flags)
        
        if flags_set > 1:
            raise click.UsageError("Only one framework can be specified: --langchain, --langgraph, or --llamaindex")

        # Determine framework from flags
        framework = ""
        if langchain:
            framework = "langchain"
        elif langgraph:
            framework = "langgraph"
        elif llamaindex:
            framework = "llamaindex"
        
        # Handle minimal case: no framework specified and no interactive mode
        use_minimal_default = not framework and not interactive
        
        if use_minimal_default:
            # For minimal default, we treat "default" as both framework and template
            # This downloads from templates/default/ (not templates/default/default/)
            framework = ""         # Empty framework 
            template = "default"   # Template is "default"

        # Use the path as the project location
        project_path = Path(path).resolve()
        relative_project_path = project_path.relative_to(Path.cwd())
        
        # Ensure the path exists (create parent directories if needed)
        project_path.parent.mkdir(parents=True, exist_ok=True)

        # Interactive framework selection (only if interactive mode and no framework flag)
        if interactive and not framework:
            templates = sdk.list_available()
            frameworks = list(templates.keys())

            console.print("🎯 [bold]Available frameworks:[/bold]")
            for i, fw in enumerate(frameworks, 1):
                console.print(f"  {i}. {fw}")

            choice = click.prompt(
                "Select framework", type=click.IntRange(1, len(frameworks)), default=1
            )
            framework = frameworks[choice - 1]

        # Interactive template selection (only if interactive mode)
        if interactive and framework:  # Only if we have a framework
            templates = sdk.list_available(framework)
            template_list = templates.get(framework, ["default"])

            console.print(f"\n🧱 [bold]Available templates for {framework}:[/bold]")
            for i, tmpl in enumerate(template_list, 1):
                console.print(f"  {i}. {tmpl}")

            choice = click.prompt(
                "Select template", type=click.IntRange(1, len(template_list)), default=1
            )
            template = template_list[choice - 1]

        # Handle minimal case: no framework specified and no interactive mode
        use_minimal_default = not framework and not interactive
        
        if use_minimal_default:
            # For minimal default, we use empty framework and "default" template
            # This will download from templates/default/ (after your downloader change)
            framework = ""         # Empty framework 
            template = "default"   # Template is "default"

        # Show configuration
        console.print(f"\n🚀 [bold]Initializing project:[/bold]")

        console.print(f"   Path: [cyan]{relative_project_path}[/cyan]")
        console.print(f"   Framework: [magenta]{framework if framework else 'None'}[/magenta]")
        console.print(f"   Template: [yellow]{template}[/yellow]")

        # Initialize project
        success = sdk.init_project(
            folder=str(project_path),
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
        console.print(f"❌ [red]Template error:[/red] {e}")
        raise click.ClickException("Project initialization failed")
    except FileExistsError as e:
        console.print(f"❌ [red]Path exists:[/red] {e}")
        console.print("💡 Use [cyan]--overwrite[/cyan] to force initialization")
        raise click.ClickException("Project initialization failed")
    except Exception as e:
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
def deploy_local(folder, framework, replace):
    """Deploy agent locally for testing"""

    try:
        sdk = RunAgent()

        # Validate folder
        if not Path(folder).exists():
            raise click.ClickException(f"Folder not found: {folder}")

        console.print(f"🚀 [bold]Deploying agent locally...[/bold]")
        console.print(f"📁 Source: [cyan]{folder}[/cyan]")

        # Deploy agent
        result = sdk.deploy_local(
            folder=folder, framework=framework, replace_agent_id=replace
        )

        if result.get("success"):
            agent_id = result["agent_id"]
            console.print(f"\n✅ [green]Local deployment successful![/green]")
            console.print(f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]")
            console.print(f"🌐 Endpoint: [link]{result.get('endpoint')}[/link]")

            if replace:
                console.print(f"🔄 Replaced agent: [yellow]{replace}[/yellow]")

            # Show capacity info
            capacity = sdk.get_local_capacity()
            console.print(
                f"📊 Capacity: [cyan]{capacity.get('current_count', 1)}/5[/cyan] slots used"
            )

            console.print(f"\n💡 [bold]Next steps:[/bold]")
            console.print(f"  • Start server: [cyan]runagent serve[/cyan]")
            console.print(
                f"  • Test agent: [cyan]runagent run --id {agent_id} --local[/cyan]"
            )
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
        console.print(f"❌ [red]Deployment error:[/red] {e}")
        raise click.ClickException("Deployment failed")


@click.command()
@click.option("--port", default=8450, help="Port to run server on")
@click.option("--host", default="127.0.0.1", help="Host to bind server to")
@click.option("--debug", is_flag=True, help="Run server in debug mode")
@click.argument(
    "path",
    type=click.Path(
        exists=True,  # Path must exist
        file_okay=False,  # Don't allow files
        dir_okay=True,  # Allow directories only
        readable=True,  # Must be readable
        resolve_path=True,  # Convert to absolute path
        path_type=Path,  # Return as pathlib.Path object
    ),
    default=".",
)
def serve(port, host, debug, path):
    """Start local FastAPI server for testing deployed agents"""

    try:
        sdk = RunAgent()

        console.print("⚡ [bold]Starting local server...[/bold]")
        console.print(f"🌐 URL: [bold blue]http://{host}:{port}[/bold blue]")
        console.print(f"📖 Docs: [link]http://{host}:{port}/docs[/link]")

        # Start server (this will block)
        sdk.serve_local_agent(agent_path=path, port=port, host=host, debug=debug)

    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
    except Exception as e:
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
@click.option("--generic", is_flag=True, help="Use generic mode (default)")
@click.option("--generic-stream", is_flag=True, help="Use generic streaming mode")
@click.option("--timeout", type=int, help="Timeout in seconds")
@click.pass_context
def run(ctx, agent_id, host, port, input_file, local, generic, generic_stream, timeout):
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
    # VALIDATION 2: Generic mode selection
    # ============================================
    if generic and generic_stream:
        raise click.UsageError(
            "Cannot specify both --generic and --generic-stream. Choose one."
        )
    
    # Default to generic mode if neither specified
    if not generic and not generic_stream:
        generic = True
        console.print("🔧 Defaulting to --generic mode")
    
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
    
    # Mode
    mode = "Generic Streaming" if generic_stream else "Generic"
    console.print(f"   Mode: [magenta]{mode}[/magenta]")
    
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
            raise click.ClickException(f"Invalid JSON in input file: {input_file}")
        except Exception as e:
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
        ra_client = RunAgentClient(agent_id, local, host, port)

        if generic_stream:
            for item in ra_client.run_generic_stream(**input_params):
                console.print(item)
        else:
            result = ra_client.run_generic(**input_params)
            console.print(result)
            
    except Exception as e:
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
            capacity_info = sdk.get_local_capacity()

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
                for i, agent in enumerate(agents):
                    status_icon = (
                        "🟢"
                        if agent["status"] == "deployed"
                        else "🔴" if agent["status"] == "error" else "🟡"
                    )
                    age_label = (
                        " (oldest)"
                        if i == 0
                        else " (newest)" if i == len(agents) - 1 else ""
                    )
                    console.print(
                        f"  {i+1}. {status_icon} [magenta]{agent['agent_id']}[/magenta] ({agent['framework']}) - {agent['deployed_at']}{age_label}"
                    )

            if capacity_info.get("is_full"):
                oldest = capacity_info.get("oldest_agent", {})
                console.print(
                    f"\n💡 [yellow]To deploy new agent, replace oldest:[/yellow]"
                )
                console.print(
                    f"   [cyan]runagent deploy-local --folder <path> --replace {oldest.get('agent_id', '')}[/cyan]"
                )

            return

        if agent_id:
            # Show specific agent info
            result = sdk.get_agent_info(agent_id, local=True)

            if result.get("success"):
                agent_info = result["agent_info"]
                console.print(f"\n📊 [bold]Agent: {agent_id}[/bold]")
                console.print(f"Status: [cyan]{agent_info['status']}[/cyan]")
                console.print(
                    f"Framework: [magenta]{agent_info['framework']}[/magenta]"
                )
                console.print(f"Deployed: [yellow]{agent_info['deployed_at']}[/yellow]")
                console.print(f"Source Path: [blue]{agent_info['folder_path']}[/blue]")
                console.print(
                    f"Deployment Path: [blue]{agent_info['deployment_path']}[/blue]"
                )

                exists_status = "✅" if agent_info.get("deployment_exists") else "❌"
                source_status = "✅" if agent_info.get("source_exists") else "❌"
                console.print(f"Files Exist: {exists_status}")
                console.print(f"Source Exists: {source_status}")

                stats = agent_info.get("stats", {})
                if stats:
                    console.print(f"\n📈 [bold]Statistics:[/bold]")
                    console.print(
                        f"Total Runs: [cyan]{stats.get('total_runs', 0)}[/cyan]"
                    )
                    console.print(
                        f"Success Rate: [green]{stats.get('success_rate', 0)}%[/green]"
                    )
                    console.print(
                        f"Last Run: [yellow]{stats.get('last_run', 'Never')}[/yellow]"
                    )
                    avg_time = stats.get("avg_execution_time")
                    if avg_time:
                        console.print(f"Avg Execution Time: [cyan]{avg_time}s[/cyan]")
            else:
                console.print(f"❌ [red]{result.get('error')}[/red]")
            return

        # Show general database stats
        stats = sdk.get_local_stats()
        capacity_info = sdk.get_local_capacity()

        console.print("\n📊 [bold]Local Database Status[/bold]")

        current_count = capacity_info.get("current_count", 0)
        is_full = capacity_info.get("is_full", False)
        status = "FULL" if is_full else "OK"
        console.print(
            f"Capacity: [cyan]{current_count}/5[/cyan] agents ([red]{status}[/red]"
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

        # List agents
        agents = sdk.list_local_agents()
        if agents:
            console.print(f"\n📋 [bold]Deployed Agents:[/bold]")
            for agent in agents:
                status_icon = (
                    "🟢"
                    if agent["status"] == "deployed"
                    else "🔴" if agent["status"] == "error" else "🟡"
                )
                exists_icon = "📁" if agent.get("exists") else "❌"
                console.print(
                    f"  {status_icon} {exists_icon} [magenta]{agent['agent_id']}[/magenta] ({agent['framework']}) - {agent['status']}"
                )

            console.print(f"\n💡 Use [cyan]--agent-id <id>[/cyan] for detailed info")
            console.print(
                f"💡 Use [cyan]--capacity[/cyan] for capacity management info"
            )

        # Cleanup if requested
        if cleanup_days:
            console.print(f"\n🧹 Cleaning up records older than {cleanup_days} days...")
            cleanup_result = sdk.cleanup_local_database(cleanup_days)
            if cleanup_result.get("success"):
                console.print(f"✅ [green]{cleanup_result.get('message')}[/green]")
            else:
                console.print(f"❌ [red]{cleanup_result.get('error')}[/red]")

    except Exception as e:
        console.print(f"❌ [red]Database status error:[/red] {e}")
        raise click.ClickException("Failed to get database status")
