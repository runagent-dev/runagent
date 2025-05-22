import click
from . import commands

# Update your CLI group
@click.group()
def runagent():
    """RunAgent CLI"""
    pass


# Add all commands to the group
runagent.add_command(commands.init)
runagent.add_command(commands.setup)
runagent.add_command(commands.teardown)
runagent.add_command(commands.template)
# runagent.add_command(template_info)

if __name__ == '__main__':
    runagent()
