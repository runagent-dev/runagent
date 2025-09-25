import click

from . import commands


@click.group()
@click.option('--version', is_flag=True, expose_value=False, is_eager=True, callback=commands.print_version, help='Show version information')
def runagent():
    """RunAgent CLI - Deploy and manage AI agents easily"""
    pass

runagent.add_command(commands.version)
runagent.add_command(commands.setup)
runagent.add_command(commands.teardown)
runagent.add_command(commands.init)
runagent.add_command(commands.template)
# runagent.add_command(commands.deploy_local)
runagent.add_command(commands.upload)
runagent.add_command(commands.start)
runagent.add_command(commands.deploy)
runagent.add_command(commands.serve)
runagent.add_command(commands.run)
runagent.add_command(commands.delete)
runagent.add_command(commands.db) 
runagent.add_command(commands.local_sync) 

if __name__ == "__main__":
    runagent()