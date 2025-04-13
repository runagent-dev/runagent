# runagent/cli/commands/logs.py
"""
Stream logs from an agent.
"""

import os
import sys
import click
import json
import time
import signal
import datetime

from ...client import RunAgentClient
from ...exceptions import RunAgentError

# Handler for Ctrl+C to exit log streaming gracefully
def handle_interrupt(signal, frame):
    click.echo("\nStopping log stream...")
    sys.exit(0)

@click.command()
@click.argument('deployment_id')
@click.option('--execution', '-e', help='Specific execution ID to stream logs for')
@click.option('--follow/--no-follow', '-f', default=True, help='Follow logs in real-time')
def logs(deployment_id, execution, follow):
    """Stream logs from a deployed agent."""
    try:
        client = RunAgentClient()
        
        # Register signal handler for Ctrl+C
        signal.signal(signal.SIGINT, handle_interrupt)
        
        if follow:
            # Define callback for WebSocket messages
            def log_callback(log_data):
                timestamp = log_data.get("timestamp", "")
                message = log_data.get("message", "")
                exec_id = log_data.get("execution_id", "")
                
                # Format timestamp
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
                
                if exec_id:
                    click.echo(f"[{timestamp}] [{exec_id[:8]}] {message}")
                else:
                    click.echo(f"[{timestamp}] {message}")
            
            # Start log streaming
            if execution:
                click.echo(f"Streaming logs for execution {execution} in deployment {deployment_id}...")
                ws = client.stream_logs(deployment_id, execution_id=execution, callback=log_callback)
            else:
                click.echo(f"Streaming logs for deployment {deployment_id}...")
                ws = client.stream_logs(deployment_id, callback=log_callback)
            
            # Keep process running to receive logs
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo("\nStopping log stream...")
                ws.close()
                
        else:
            # Get deployment status to fetch recent logs
            if execution:
                result = client.get_execution_status(deployment_id, execution)
                logs_data = result.get("recent_logs", [])
            else:
                result = client.get_status(deployment_id)
                logs_data = result.get("recent_logs", [])
            
            if not logs_data:
                click.echo("No logs available.")
                return
            
            # Display logs
            for log in logs_data:
                timestamp = log.get("timestamp", "")
                message = log.get("message", "")
                exec_id = log.get("execution_id", "")
                
                # Format timestamp
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
                
                if exec_id:
                    click.echo(f"[{timestamp}] [{exec_id[:8]}] {message}")
                else:
                    click.echo(f"[{timestamp}] {message}")
                
    except RunAgentError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
