# runagent/cli/commands/deploy.py
"""
Deploy an agent.
"""

import os
import sys
import click
import time
from pathlib import Path

from ...client import RunAgentClient
from ...exceptions import RunAgentError, DeploymentError
from ...utils import validate_agent_directory

@click.command()
@click.argument('path', type=click.Path(exists=True), default=".")
@click.option('--type', '-t', default='langgraph', help='Agent framework type')
@click.option('--wait/--no-wait', default=True, help='Wait for deployment to complete')
def deploy(path, type, wait):
    """Deploy an agent from the given path."""
    try:
        # Validate the path
        path = Path(path).resolve()
        validate_agent_directory(path)
        
        click.echo(f"Deploying agent from {path}...")
        
        # Deploy the agent
        client = RunAgentClient()
        result = client.deploy(path, agent_type=type)
        
        deployment_id = result.get("deployment_id")
        
        click.echo(f"Deployment initiated with ID: {deployment_id}")
        click.echo(f"Initial status: {result.get('status')}")
        
        # Wait for deployment to complete if requested
        if wait:
            click.echo("Waiting for deployment to complete...")
            
            max_wait = 60  # Maximum wait time in seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_result = client.get_status(deployment_id)
                status = status_result.get("status")
                
                click.echo(f"Status: {status}")
                
                if status == "running":
                    click.echo(f"Deployment complete! Agent is now running.")
                    return
                elif status == "failed":
                    click.echo(f"Deployment failed: {status_result.get('error', 'Unknown error')}", err=True)
                    sys.exit(1)
                
                time.sleep(2)
            
            click.echo("Deployment is taking longer than expected. "
                      f"Check status later with 'runagent status {deployment_id}'")
        
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)