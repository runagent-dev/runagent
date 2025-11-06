import os
import click
import warnings
from rich.console import Console

from . import commands
from .branding import print_logo


from .commands.setup import setup as setup_cmd
from .commands.config import config as config_cmd
from .commands.teardown import teardown as teardown_cmd 
from .commands.init import init as init_cmd
from .commands.upload import upload as upload_cmd
from .commands.start import start as start_cmd
from .commands.deploy import deploy as deploy_cmd
from .commands.serve import serve as serve_cmd
from .commands.run import run as run_cmd
from .commands.run_stream import run_stream as run_stream_cmd
from .commands.db import db as db_cmd
from .commands.whoami import whoami as whoami_cmd

if not os.getenv('DISABLE_TRY_CATCH'):
    warnings.filterwarnings(
        "ignore",
        message=".*Pydantic serializer warnings.*"
    )

def show_help_with_logo(ctx, param, value):
    """Custom help callback that shows logo before help text"""
    if value and not ctx.resilient_parsing:
        print_logo(show_tagline=True, brand_color="cyan")
        click.echo(ctx.get_help())
        ctx.exit()

console = Console()


def print_version(ctx, param, value):
    """Custom version callback with colored output"""
    if not value or ctx.resilient_parsing:
        return
    try:
        from runagent.__version__ import __version__
        from runagent.cli.branding import print_compact_logo
        print_compact_logo(brand_color="cyan")
        console.print(f"\n[bold white]Version:[/bold white] [bold cyan]{__version__}[/bold cyan]")
        console.print(f"[dim]Deploy and manage AI agents with ease 🚀[/dim]\n")
    except ImportError:
        console.print("[red]runagent version unknown[/red]")
    ctx.exit()


@click.group(invoke_without_command=True)
@click.option('--help', '-h', is_flag=True, expose_value=False, is_eager=True, callback=show_help_with_logo, help='Show this message and exit')
@click.option('--version', is_flag=True, expose_value=False, is_eager=True, callback=print_version, help='Show version information')
@click.pass_context
def runagent(ctx):
    """RunAgent CLI - Deploy and manage AI agents easily"""
    # Show logo when no subcommand is provided
    if ctx.invoked_subcommand is None:
        print_logo(show_tagline=True, brand_color="cyan")
        click.echo(ctx.get_help())

runagent.add_command(setup_cmd)
runagent.add_command(config_cmd)
runagent.add_command(teardown_cmd)
runagent.add_command(init_cmd)
runagent.add_command(upload_cmd)
runagent.add_command(start_cmd)
runagent.add_command(deploy_cmd)
runagent.add_command(serve_cmd)
runagent.add_command(run_cmd)
runagent.add_command(run_stream_cmd)
runagent.add_command(db_cmd)
runagent.add_command(whoami_cmd) 

if __name__ == "__main__":
    runagent()