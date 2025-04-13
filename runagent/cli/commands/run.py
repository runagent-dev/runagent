# runagent/cli/commands/run.py
"""
Run a deployed agent.
"""

import os
import sys
import click
import json
import time

from ...client import RunAgentClient
from ...exceptions import RunAgentError

@click.command()
@click.argument('deployment_id')
@click.option('--input', '-i', type=click.Path(exists=True), help='JSON input file path')
@click.option('--webhook', '-w', help='Webhook URL for result notification')
@click.option('--wait/--no-wait', default=True, help='Wait for execution to complete')
@click.option('--json-input', help='JSON input as a string')
def run(deployment_id, input, webhook, wait, json_input):
    """Run a deployed agent."""
    try:
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
        
        client = RunAgentClient()
        
        # Run the agent
        click.echo(f"Triggering agent {deployment_id} with input: {json.dumps(input_data, indent=2)}")
        result = client.run_agent(deployment_id, input_data, webhook_url=webhook)
        
        execution_id = result.get("execution_id")
        click.echo(f"Execution started with ID: {execution_id}")
        click.echo(f"Status: {result.get('status')}")
        
        # Wait for execution to complete if requested
        if wait:
            click.echo("Waiting for execution to complete...")
            
            max_wait = 300  # Maximum wait time in seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_result = client.get_execution_status(deployment_id, execution_id)
                status = status_result.get("status")
                
                click.echo(f"Status: {status}")
                
                if status in ["completed", "failed"]:
                    if status == "completed":
                        click.echo("Execution completed successfully!")
                        if "output" in status_result:
                            click.echo("\nOutput:")
                            click.echo(json.dumps(status_result["output"], indent=2))
                    else:
                        click.echo(f"Execution failed: {status_result.get('error', 'Unknown error')}", err=True)
                    return
                
                time.sleep(2)
            
            click.echo("Execution is taking longer than expected. "
                     f"Check status later with 'runagent status {deployment_id}'")
        
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)