import click

from . import commands
from .branding import print_logo


def show_help_with_logo(ctx, param, value):
    """Custom help callback that shows logo before help text"""
    if value and not ctx.resilient_parsing:
        print_logo(show_tagline=True, brand_color="cyan")
        click.echo(ctx.get_help())
        ctx.exit()


@click.group(invoke_without_command=True)
@click.option('--help', '-h', is_flag=True, expose_value=False, is_eager=True, callback=show_help_with_logo, help='Show this message and exit')
@click.option('--version', is_flag=True, expose_value=False, is_eager=True, callback=commands.print_version, help='Show version information')
@click.pass_context
def runagent(ctx):
    """RunAgent CLI - Deploy and manage AI agents easily"""
    # Show logo when no subcommand is provided
    if ctx.invoked_subcommand is None:
        print_logo(show_tagline=True, brand_color="cyan")
        click.echo(ctx.get_help())

runagent.add_command(commands.setup)
runagent.add_command(commands.config)  # Config command group
runagent.add_command(commands.teardown)
runagent.add_command(commands.init)
runagent.add_command(commands.template)
runagent.add_command(commands.upload)
runagent.add_command(commands.start)
runagent.add_command(commands.deploy)
runagent.add_command(commands.serve)
runagent.add_command(commands.run)
runagent.add_command(commands.run_stream)
runagent.add_command(commands.delete)
runagent.add_command(commands.db) 

if __name__ == "__main__":
    runagent()