# runagent/cli/commands/status.py
"""
Check the status of a deployed agent.
"""

import os
import sys
import click
import json
from datetime import datetime

from ...client import RunAgentClient
from ...exceptions import RunAgentError

@click.command()
@click.argument('deployment_id')
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
def status(deployment_id, output_json):
    """Check the status of a deployed agent."""
    try:
        client = RunAgentClient()
        result = client.get_status(deployment_id)
        
        if output_json:
            click.echo(json.dumps(result, indent=2))
            return
        
        # Format output for human readability
        click.echo(f"Agent: {deployment_id}")
        click.echo(f"Status: {result['status']}")
        click.echo(f"Created: {result['created_at']}")
        click.echo(f"Updated: {result['updated_at']}")
        
        if result.get("container_id"):
            click.echo(f"Container ID: {result['container_id']}")

        if result.get("host_port"):
            click.echo(f"Port: {result['host_port']}")
            
        if result.get("error"):
            click.echo(f"Error: {result['error']}")
        
        # Display recent executions if available
        if "recent_executions" in result and result["recent_executions"]:
            click.echo("\nRecent executions:")
            for idx, exec_info in enumerate(result["recent_executions"]):
                click.echo(f"  {idx+1}. {exec_info['execution_id']} - {exec_info['status']} ({exec_info['created_at']})")
        else:
            click.echo("\nNo recent executions.")
            
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)