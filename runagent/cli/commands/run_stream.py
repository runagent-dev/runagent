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
    
    console.print("[bold]RunAgent Streaming Configuration:[/bold]")
    
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

        console.print(f"\n[bold]Starting streaming execution...[/bold]")
        console.print(f"[dim]Connected to agent via WebSocket[/dim]")
        console.print(f"[dim]Streaming results:[/dim]\n")
        
        # Stream the results
        for chunk in ra_client.run_stream(**input_params):
            console.print(chunk)
            
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
        console.print(f"❌ [bold red]Streaming failed:[/bold red] {e}")
        # Exit with error code 1 instead of raising ClickException to avoid duplicate message
        import sys
        sys.exit(1)

