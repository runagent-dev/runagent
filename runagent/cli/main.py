# runagent/cli/main.py
"""
Main CLI entrypoint for RunAgent.
"""

import os
import sys
import click
import json

from ..client import RunAgentClient
from ..config import get_config, set_config
from ..exceptions import RunAgentError, AuthenticationError
from ..utils import validate_agent_directory
from .. import __version__

# Import commands
from .commands.init import init
from .commands.deploy import deploy
from .commands.status import status
from .commands.logs import logs
from .commands.run import run
from .commands.sandbox import sandbox

@click.group()
@click.version_option(version=__version__)
def cli():
    """RunAgent CLI - Deploy and manage AI agents."""
    pass


# Add commands
cli.add_command(init)
cli.add_command(deploy)
cli.add_command(status)
cli.add_command(logs)
cli.add_command(run)
cli.add_command(sandbox)

@cli.command()
@click.option('--api-key', help='Your RunAgent API key')
@click.option('--base-url', help='Custom API base URL')
def configure(api_key, base_url):
    """Configure the RunAgent CLI."""
    config = {}
    
    if api_key:
        config["api_key"] = api_key
    
    if base_url:
        config["base_url"] = base_url
    
    if not config:
        # Display current configuration
        current_config = get_config()
        masked_key = "****" + current_config.get("api_key", "")[-4:] if current_config.get("api_key") else "Not set"
        
        click.echo("Current configuration:")
        click.echo(f"API Key: {masked_key}")
        click.echo(f"Base URL: {current_config.get('base_url')}")
        
        # Interactive configuration
        if click.confirm("Would you like to update your configuration?"):
            if click.confirm("Update API key?"):
                new_key = click.prompt("Enter your API key", hide_input=True)
                config["api_key"] = new_key
            
            if click.confirm("Update base URL?"):
                new_url = click.prompt("Enter base URL", default=current_config.get("base_url"))
                config["base_url"] = new_url
    
    if config:
        try:
            set_config(config)
            click.echo("Configuration updated successfully.")
        except Exception as e:
            click.echo(f"Error updating configuration: {e}", err=True)
            sys.exit(1)

@cli.command()
def health():
    """Check the health of the RunAgent service."""
    try:
        client = RunAgentClient()
        result = client.api.get("")  # Root endpoint (health check)
        click.echo(f"Service is healthy: {result}")
    except AuthenticationError:
        # Don't fail on auth error for health check
        click.echo("Service appears to be running, but you're not authenticated.")
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('deployment_id')
def delete(deployment_id):
    """Delete a deployed agent."""
    try:
        client = RunAgentClient()
        
        if click.confirm(f"Are you sure you want to delete agent {deployment_id}?"):
            result = client.delete_agent(deployment_id)
            click.echo(f"Agent {deployment_id} deletion initiated.")
            click.echo(f"Status: {result['status']}")
        else:
            click.echo("Deletion cancelled.")
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--status', help='Filter by status (e.g., running, failed)')
def list(status):
    """List all your agent deployments."""
    try:
        client = RunAgentClient()
        deployments = client.list_deployments(status=status)
        
        if not deployments:
            click.echo("No deployments found." + (f" (with status: {status})" if status else ""))
            return
        
        # Format output as a table
        click.echo(f"{'DEPLOYMENT ID':<36} {'STATUS':<12} {'CREATED':<20} {'EXECUTIONS'}")
        click.echo("-" * 80)
        
        for d in deployments:
            click.echo(f"{d['deployment_id']:<36} {d['status']:<12} {d['created_at'][:19]:<20} {d.get('execution_count', 0)}")
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()