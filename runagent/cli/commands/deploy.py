"""
CLI commands that use the restructured SDK internally.
"""
import os
import tempfile
from typing import Optional, Tuple

from pathlib import Path

import click
from rich.console import Console

from runagent import RunAgentSDK
from runagent.sdk.exceptions import (  # RunAgentError,; ConnectionError
    AuthenticationError,
    TemplateError,
)
from runagent.constants import TEMPLATE_PREPATH
console = Console()


def format_error_message(error_info):
    """Format error information from API responses"""
    if isinstance(error_info, dict) and "message" in error_info:
        error_message = error_info.get("message", "Unknown error")
        error_code = error_info.get("code")
        if error_code:
            return f"[{error_code}] {error_message}"
        return error_message
    return str(error_info) if error_info else "Unknown error"


# ============================================================================
# Config Command Group
# ============================================================================


def _resolve_template_path(template_path: str) -> Tuple[Path, Optional[Path]]:
    """
    Resolve template path - supports both:
    - Direct paths: "templates/openclaw/gateway" or "./my-agent"
    - Template shortcuts: "openclaw/gateway" (resolves to templates/openclaw/gateway)
    
    Returns:
        Tuple of (resolved_path, temp_dir_for_cleanup)
        temp_dir_for_cleanup is None if path is local (not downloaded)
    """
    # Support single-token aliases before path resolution
    # e.g. "picoclaw" -> "picoclaw/gateway"
    if template_path == "picoclaw":
        template_path = "picoclaw/gateway"

    path = Path(template_path)
    
    # If path exists, use it directly
    if path.exists():
        return path.resolve(), None
    
    # Check if it looks like a template shortcut (framework/template format)
    parts = template_path.split("/")
    if len(parts) == 2 and "/" in template_path:
        framework, template = parts
        
        # First, check if local template exists
        # Try multiple locations:
        # 1. Current working directory (if in runagent source repo)
        # 2. Parent of runagent package (if templates are alongside package)
        # 3. Relative to runagent package location
        possible_paths = [
            Path.cwd() / TEMPLATE_PREPATH / framework / template,  # Current dir
            Path.cwd() / "templates" / framework / template,  # Current dir with "templates"
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
                console.print(f"[dim]Using local template: [cyan]{framework}/{template}[/cyan][/dim]")
                return local_template_path.resolve(), None
        
        # If local doesn't exist, try to download from remote
        try:
            sdk = RunAgentSDK()
            temp_dir = tempfile.mkdtemp(prefix="runagent-deploy-")
            temp_path = Path(temp_dir) / template
            
            console.print(f"[dim]Downloading template: [cyan]{framework}/{template}[/cyan][/dim]")
            sdk.templates.init_template(
                folder_path=temp_path,
                framework=framework,
                template=template,
                overwrite=True
            )
            
            if temp_path.exists():
                console.print(f"[green]✓[/green] Template downloaded to temporary directory")
                return temp_path.resolve(), Path(temp_dir)
            else:
                raise TemplateError(f"Template download failed: {framework}/{template}")
        except Exception as e:
            raise click.ClickException(
                f"Template '{template_path}' not found locally or remotely. "
                f"Available formats: 'framework/template' (e.g., 'openclaw/gateway') or a local path.\n"
                f"Error: {e}"
            )
    
    # Check if it's templates/framework/template format
    if template_path.startswith("templates/") or template_path.startswith(f"{TEMPLATE_PREPATH}/"):
        # Remove templates/ prefix and try as shortcut
        shortcut = template_path.replace(f"{TEMPLATE_PREPATH}/", "").replace("templates/", "")
        return _resolve_template_path(shortcut)
    
    # Path doesn't exist and doesn't look like a template
    raise click.ClickException(
        f"Path not found: {path}\n"
        f"Use a local path or template shortcut like 'openclaw/gateway' or 'picoclaw/gateway'"
    )


@click.command()
@click.option("--overwrite", is_flag=True, help="Overwrite existing agent if it already exists")
@click.option(
    "--new-id",
    is_flag=True,
    help="Do NOT reuse existing agent ID for template shortcuts (e.g. always create a new agent for 'openclaw/gateway')",
)
@click.argument(
    "path",
    type=str,
    default=".",
)
def deploy(path: str, overwrite: bool, new_id: bool):
    """
    Deploy agent (upload + start) to remote server.
    
    PATH can be:
    - A local folder: "./my-agent" or "/path/to/agent"
    - A template shortcut: "openclaw/gateway" or "openclaw/mcp"
    - A template path: "templates/openclaw/gateway"
    
    Examples:
        runagent deploy .                    # Deploy current directory
        runagent deploy openclaw/gateway     # Deploy OpenClaw gateway template
        runagent deploy openclaw/mcp         # Deploy OpenClaw MCP template
        runagent deploy templates/openclaw/gateway  # Same as above
    """

    try:
        from runagent.cli.branding import print_header
        print_header("Deploy Agent")
        
        sdk = RunAgentSDK()

        # Check authentication
        if not sdk.is_configured():
            console.print(
                "❌ [red]Not authenticated.[/red] Run [cyan]'runagent setup --api-key <key>'[/cyan] first"
            )
            raise click.ClickException("Authentication required")

        # Resolve template path (downloads template if needed)
        try:
            resolved_path, temp_dir_to_cleanup = _resolve_template_path(path)
        except click.ClickException:
            raise
        except Exception as e:
            raise click.ClickException(f"Failed to resolve path '{path}': {e}")

        console.print(f"[bold]Deploying agent (upload + start)...[/bold]")
        console.print(f"Source: [cyan]{resolved_path}[/cyan]")

        # Check if agent needs registration (has null UUID or not registered)
        from runagent.utils.agent import get_agent_config
        from runagent.utils.agent_id import generate_agent_id
        from runagent.sdk.db import DBService
        from runagent.constants import LOCAL_CACHE_DIRECTORY
        import json
        import shutil
        
        NULL_UUID = "00000000-0000-0000-0000-000000000000"
        config_path = resolved_path / "runagent.config.json"
        needs_registration = False
        working_path = resolved_path
        working_temp_dir = None  # Track if we created a working copy
        
        # Check if this is a template shortcut (e.g., "openclaw/gateway")
        is_template_shortcut = "/" in path and not Path(path).exists()
        reuse_agent_id = None
        
        # Only try to reuse existing agent ID when *not* forcing a new one
        if is_template_shortcut and not new_id:
            # Check if we've deployed this template before by looking in database
            try:
                agent_config = get_agent_config(resolved_path)
                template_name = agent_config.get('template') if isinstance(agent_config, dict) else getattr(agent_config, 'template', None)
                agent_name = agent_config.get('agent_name') if isinstance(agent_config, dict) else getattr(agent_config, 'agent_name', None)
                
                if template_name or agent_name:
                    db_service = DBService()
                    from runagent.sdk.db import Agent
                    from sqlalchemy import or_
                    with db_service.db_manager.get_session() as session:
                        query = session.query(Agent)
                        conditions = []
                        if template_name:
                            conditions.append(Agent.template == template_name)
                        if agent_name:
                            conditions.append(Agent.agent_name == agent_name)
                        if conditions:
                            query = query.filter(or_(*conditions))
                            existing_agents = query.order_by(Agent.created_at.desc()).all()
                            
                            if existing_agents:
                                # Use the most recently created agent with this template
                                reuse_agent_id = existing_agents[0].agent_id
                                console.print(f"[green]✓[/green] Reusing existing agent ID: [cyan]{reuse_agent_id}[/cyan]")
                                console.print(f"[dim]Template '{path}' was previously deployed[/dim]")
            except Exception as e:
                # Silently continue - will generate new UUID
                pass
        
        # If deploying from a template, we may need to create a working copy
        if config_path.exists():
            try:
                agent_config = get_agent_config(resolved_path)
                agent_id = agent_config.get('agent_id') if isinstance(agent_config, dict) else getattr(agent_config, 'agent_id', None)
                
                # Check if agent_id is null UUID or missing
                if not agent_id or agent_id == NULL_UUID:
                    # If we found an existing agent_id for this template shortcut, reuse it
                    if reuse_agent_id:
                        new_agent_id = reuse_agent_id
                        needs_registration = False  # Already registered
                    else:
                        needs_registration = True
                        new_agent_id = generate_agent_id()
                        console.print(f"[dim]Agent has null UUID, generating new ID[/dim]")
                    
                    # If this is a local template (not a temp download), create a working copy
                    # to avoid modifying the original template
                    if temp_dir_to_cleanup is None:
                        # Create a temporary working copy to avoid modifying the template
                        import tempfile
                        working_temp_dir = Path(tempfile.mkdtemp(prefix="runagent-deploy-working-"))
                        working_path = working_temp_dir / resolved_path.name
                        shutil.copytree(resolved_path, working_path)
                        console.print(f"[dim]Created working copy: [cyan]{working_path}[/cyan][/dim]")
                        config_path = working_path / "runagent.config.json"
                    # else: temp_dir_to_cleanup exists, so resolved_path is already a temp copy
                    # and we can safely modify it
                    
                    # Update config with agent ID (either reused or new)
                    with config_path.open('r') as f:
                        config_data = json.load(f)
                    config_data['agent_id'] = new_agent_id
                    with config_path.open('w') as f:
                        json.dump(config_data, f, indent=2)
                    
                    if reuse_agent_id:
                        console.print(f"[green]✓[/green] Using existing agent ID: [cyan]{new_agent_id}[/cyan]")
                    else:
                        console.print(f"[green]✓[/green] Generated agent ID: [cyan]{new_agent_id}[/cyan]")
                    
                else:
                    # Check if agent is registered in database
                    db_service = DBService()
                    existing_agent = db_service.get_agent(agent_id)
                    if not existing_agent:
                        needs_registration = True
                        console.print(f"[dim]Agent {agent_id} not registered, will register now[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Could not check agent registration: {e}")
                # Continue with deployment anyway
        
        # Register agent if needed
        if needs_registration:
            try:
                from .register import _register_agent_core
                console.print(f"[dim]Registering agent...[/dim]")
                _register_agent_core(working_path)
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Registration warning: {e}")
                # Continue with deployment anyway - remote might handle it
        
        # If we're reusing an agent ID, update the agent path in database
        # (since each deployment creates a new temporary working copy)
        if reuse_agent_id and not needs_registration:
            try:
                db_service = DBService()
                # Directly update agent_path in database
                from runagent.sdk.db import Agent
                with db_service.db_manager.get_session() as session:
                    agent = session.query(Agent).filter(Agent.agent_id == reuse_agent_id).first()
                    if agent:
                        agent.agent_path = str(working_path)
                        session.commit()
                        console.print(f"[dim]Updated agent path in database[/dim]")
            except Exception as e:
                # Silently continue - path update is not critical
                pass

        try:
            # Deploy agent (framework auto-detected)
            result = sdk.deploy_remote(folder=str(working_path), overwrite=overwrite)
        finally:
            # Cleanup temp directories
            if temp_dir_to_cleanup and temp_dir_to_cleanup.exists():
                try:
                    shutil.rmtree(temp_dir_to_cleanup)
                    console.print(f"[dim]Cleaned up temporary template directory[/dim]")
                except Exception:
                    pass  # Ignore cleanup errors
            
            # Cleanup working copy if we created one
            if working_temp_dir is not None and working_temp_dir.exists():
                try:
                    shutil.rmtree(working_temp_dir)
                    console.print(f"[dim]Cleaned up working copy[/dim]")
                except Exception:
                    pass  # Ignore cleanup errors

        if result.get("success"):
            agent_id = result.get('agent_id')
            dashboard_url = result.get('dashboard_url') or f"https://app.run-agent.ai/dashboard/agents/{agent_id}"
            
            console.print(f"\n✅ [green]Deployment successful![/green]")
            console.print(f"Agent ID: [bold magenta]{agent_id}[/bold magenta]")
            console.print(f"Agent URL: [link]{dashboard_url}[/link]")
            
            # Check if this looks like an OpenClaw Gateway deployment (by path/shortcut),
            # then display gateway URL + token + pairing info + VM IP for MCP setup.
            try:
                is_openclaw_gateway = (
                    "openclaw/gateway" in path
                    or path.endswith("openclaw/gateway")
                    or path.rstrip("/").endswith("gateway") and "openclaw" in str(path)
                )
                is_picoclaw_gateway = (
                    path == "picoclaw"
                    or "picoclaw/gateway" in path
                    or path.endswith("picoclaw/gateway")
                )
                
                if is_openclaw_gateway:
                    # Fetch agent metadata and NetworkInfo to get all credentials.
                    # Poll a few times since serverless gateway setup runs in background.
                    import time
                    gateway_url = None
                    gateway_token = None
                    pairing_status = None
                    vm_ip = None
                    
                    # Check if result already has NetworkInfo (from start response)
                    if result.get("network_info"):
                        network_info = result.get("network_info", {})
                        vm_ip = network_info.get("ip_address") or network_info.get("IpAddress")
                    elif result.get("data") and result.get("data", {}).get("network_info"):
                        network_info = result.get("data", {}).get("network_info", {})
                        vm_ip = network_info.get("ip_address") or network_info.get("IpAddress")
                    
                    for attempt in range(5):  # Try up to 5 times
                        time.sleep(1 + attempt)  # Increasing wait: 1s, 2s, 3s, 4s, 5s
                        agent_info = sdk.remote.client.get_agent_status(agent_id)
                        if agent_info.get("success"):
                            data = agent_info.get("data", {}) or {}
                            
                            # Extract NetworkInfo
                            network_info = data.get("network_info") or {}
                            if not vm_ip:
                                vm_ip = network_info.get("ip_address") or network_info.get("IpAddress")
                            
                            # Extract metadata
                            metadata = data.get("metadata", {}) or {}
                            gateway_url = metadata.get("gateway_url") or gateway_url
                            gateway_token = metadata.get("gateway_token") or gateway_token
                            pairing_status = metadata.get("pairing_status") or pairing_status
                            
                            # If we have URL or IP, we consider setup "good enough" to show.
                            if gateway_url or vm_ip:
                                break
                    
                    # Prefer token from environment if present (user-controlled secret)
                    env_gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN") or None
                    if env_gateway_token:
                        gateway_token = env_gateway_token

                    console.print(f"\n[bold cyan]OpenClaw Gateway Credentials:[/bold cyan]")
                    console.print(f"  Agent ID: [bold magenta]{agent_id}[/bold magenta]")
                    
                    if vm_ip:
                        console.print(f"  VM IP Address: [green]{vm_ip}[/green]")
                    else:
                        console.print(f"  VM IP Address: [yellow]Not yet available (VM still starting)[/yellow]")
                    
                    if gateway_url:
                        console.print(f"  Gateway URL: [green]{gateway_url}[/green]")
                    elif vm_ip:
                        # Construct gateway URL from IP if we have it
                        gateway_url = f"ws://{vm_ip}:18789"
                        console.print(f"  Gateway URL: [green]{gateway_url}[/green]")
                    else:
                        console.print(f"  Gateway URL: [yellow]Not yet available (gateway still starting)[/yellow]")
                    
                    if gateway_token:
                        console.print(f"  Gateway Token: [green]{gateway_token}[/green]")
                    elif gateway_url or vm_ip:
                        console.print(f"  Gateway Token: [yellow]Not set (token auth disabled or not provided)[/yellow]")
                    
                    if pairing_status:
                        console.print(f"  Pairing Status: [green]{pairing_status}[/green]")
                    else:
                        console.print(f"  Pairing Status: [yellow]Pending (will auto‑approve when devices connect)[/yellow]")
                    
                    if gateway_url or vm_ip:
                        console.print(f"\n[dim]Use these credentials to deploy MCP:[/dim]")
                        if gateway_url:
                            console.print(f"  [cyan]OPENCLAW_GATEWAY_URL={gateway_url}[/cyan]")
                        elif vm_ip:
                            console.print(f"  [cyan]OPENCLAW_GATEWAY_URL=ws://{vm_ip}:18789[/cyan]")
                        if gateway_token:
                            console.print(f"  [cyan]OPENCLAW_GATEWAY_TOKEN={gateway_token}[/cyan]")
                    else:
                        console.print(f"\n[dim]You can fetch gateway info later with:[/dim]")
                        console.print(f"  [cyan]runagent status {agent_id}[/cyan]")

                if is_picoclaw_gateway:
                    console.print(f"\n[bold cyan]Picoclaw Gateway Deployment:[/bold cyan]")
                    console.print(f"  Agent ID: [bold magenta]{agent_id}[/bold magenta]")
                    console.print("  Framework: [green]picoclaw[/green]")
                    console.print("  Runtime:   [green]picoclaw-gateway[/green]")
                    console.print("\n[dim]Inside the microVM, picoclaw uses:[/dim]")
                    console.print("  Config:    [cyan]/root/.picoclaw/config.json[/cyan]")
                    console.print("  Workspace: [cyan]/root/.picoclaw/workspace[/cyan]")
                    console.print("  (backed by /persistent/.picoclaw on the VM data disk)")
                    console.print("\n[dim]Next steps:[/dim]")
                    console.print("  1. Configure models and channels in ~/.picoclaw/config.json")
                    console.print("  2. Use 'picoclaw gateway' inside the VM for channel bots")
                    console.print("  3. Rely on heartbeat/cron for periodic tasks from the workspace")
            except Exception as e:
                # Log error but don't fail deployment
                import traceback
                console.print(f"[yellow]⚠[/yellow] Could not fetch gateway credentials: {e}")
                if os.getenv('DEBUG'):
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                pass
        else:
            error_info = result.get("error")
            console.print(f"❌ [red]Deployment failed:[/red] {format_error_message(error_info)}")
            if isinstance(error_info, dict):
                suggestion = error_info.get("suggestion")
                if suggestion:
                    console.print(f"[cyan]Suggestion: {suggestion}[/cyan]")
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

