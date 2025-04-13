# runagent/cli/commands/init.py
"""
Initialize a new agent project.
"""

import os
import sys
import click
from pathlib import Path
import shutil

from ...templates import create_project_from_template

@click.command()
@click.argument('path', type=click.Path(), default=".")
@click.option('--platform', '-p', default='langgraph', help='Agent platform (e.g., langgraph)')
@click.option('--template', '-t', default='default', help='Template to use')
def init(path, platform, template):
    """Initialize a new agent project."""
    try:
        # Resolve the target path
        target_path = Path(path).resolve()
        
        # Create directory if it doesn't exist
        if not target_path.exists():
            os.makedirs(target_path)
        elif not target_path.is_dir():
            click.echo(f"Error: {target_path} is not a directory", err=True)
            sys.exit(1)
        elif any(target_path.iterdir()):
            if not click.confirm(f"Directory {target_path} is not empty. Continue?"):
                click.echo("Initialization cancelled.")
                return
        
        # Create project from template
        create_project_from_template(target_path, platform, template)
        
        click.echo(f"Initialized {platform} agent project in {target_path}")
        click.echo(f"You can now cd into {target_path} and modify the agent code.")
        click.echo("Once you're ready, deploy it with 'runagent deploy'.")
        
    except Exception as e:
        click.echo(f"Error initializing project: {e}", err=True)
        sys.exit(1)