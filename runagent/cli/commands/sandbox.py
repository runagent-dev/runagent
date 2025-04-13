# runagent/cli/commands/sandbox.py
"""
Run an agent in sandbox mode.
"""

import os
import sys
import click
import json
import time
from pathlib import Path

from ...client import RunAgentClient
from ...exceptions import RunAgentError
from ...utils import validate_agent_directory

@click.command()
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--input', '-i', type=click.Path(exists=True), help='JSON input file path')
@click.option('--type', '-t', default='langgraph', help='Agent framework type')
@click.option('--json-input', help='JSON input as a string')
def sandbox(path, input, type, json_input):
    """Run an agent in sandbox mode."""
    try:
        # Validate the path
        path = Path(path).resolve()
        validate_agent_directory(path)
        
        # Parse input
        input_data = {}
        
        if input:
            try:
                with open(input, 'r') as f:
                    input_data = json.load(f)
            except json.JSONDecodeError:
                click.echo(f"Error: Invalid JSON in input file", err=True)
                sys.exit(1)
        elif json_input:
            try:
                input_data = json.loads(json_input)
            except json.JSONDecodeError:
                click.echo(f"Error: Invalid JSON input", err=True)
                sys.exit(1)
        else:
            # Interactive mode if no input is provided
            if click.confirm("No input specified. Would you like to enter input interactively?"):
                text = click.prompt("Enter your query")
                input_data = {"query": text}
            else:
                input_data = {}
        
        click.echo(f"Running {type} agent from {path} in sandbox mode...")
        click.echo(f"Input: {json.dumps(input_data, indent=2)}")
        
        # Run the agent in sandbox
        client = RunAgentClient()
        result = client.run_sandbox(path, input_data, agent_type=type)
        
        sandbox_id = result.get("sandbox_id")
        click.echo(f"Sandbox execution started with ID: {sandbox_id}")
        
        # Check for logs URL
        if "logs_url" in result:
            click.echo(f"Logs available at: {result['logs_url']}")
        
        # Wait for execution to complete
        click.echo("Waiting for sandbox execution to complete...")
        
        max_wait = 120  # Maximum wait time in seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_result = client.api.get(f"sandbox/status/{sandbox_id}")
            status = status_result.get("status")
            
            click.echo(f"Status: {status}")
            
            if status in ["completed", "failed"]:
                if status == "completed":
                    click.echo("Sandbox execution completed successfully!")
                    if "output" in status_result:
                        click.echo("\nOutput:")
                        click.echo(json.dumps(status_result["output"], indent=2))
                        
                    if "output_url" in status_result:
                        click.echo(f"\nDetailed output available at: {status_result['output_url']}")
                else:
                    click.echo(f"Sandbox execution failed: {status_result.get('error', 'Unknown error')}", err=True)
                    
                # Show logs
                if "logs" in status_result:
                    click.echo("\nExecution logs:")
                    for log in status_result["logs"]:
                        click.echo(f"[{log.get('timestamp', '')}] {log.get('message', '')}")
                
                return
            
            time.sleep(2)
        
        click.echo("Sandbox execution is taking longer than expected. "
                 f"Check status later with the provided sandbox ID.")
        
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)