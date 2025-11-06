"""
CLI command for checking RunAgent configuration status.
"""
import os
import click
from rich.console import Console

from .config import _show_config_status

console = Console()


@click.command()
def whoami():
    """Show current RunAgent configuration status"""
    try:
        _show_config_status()
    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"[red]Error:[/red] {e}")
        raise click.ClickException("Failed to show configuration status")

