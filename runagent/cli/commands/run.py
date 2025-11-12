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
from runagent.client.client import RunAgentClient, RunAgentExecutionError
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
        console.print("[yellow]No input file or extra parameters provided. Running with defaults.[/yellow]")
    
    # ============================================
    # DISPLAY CONFIGURATION
    # ============================================
    
    console.print("[bold]RunAgent Configuration:[/bold]")
    
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
            console.print(f"     {key} = [green]{value}[/green]")
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
            
    except RunAgentExecutionError as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"[bold red]❌ {e.message}[/bold red]")
        if e.suggestion:
            console.print(f"[cyan]Suggestion: {e.suggestion}[/cyan]")
        import sys
        sys.exit(1)

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        # Display error with red ❌ symbol
        console.print(f"❌ [bold red]Execution failed:[/bold red] {e}")
        # Exit with error code 1 instead of raising ClickException to avoid duplicate message
        import sys
        sys.exit(1)
