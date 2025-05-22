import click
from runagent.client import RunAgentClient


@click.command()
@click.option('--api-key', required=True, help='Your API key')
@click.option('--base-url', help='API base URL')
@click.option('--force', is_flag=True, help='Force reconfiguration')
def setup(api_key, base_url, force):
    """Setup RunAgent authentication"""
    client = RunAgentClient(cli_mode=True)  # Enable interactive mode
    client.setup(api_key=api_key, base_url=base_url, force=force)


@click.command()
@click.option('--yes', is_flag=True, help='Skip confirmation')
def teardown(yes):
    """Remove RunAgent configuration"""
    client = RunAgentClient(cli_mode=True)  # Enable interactive mode
    client.teardown(confirm=yes)


@click.command()
@click.option('--folder', help='Project folder name')
@click.option('--framework', default=None, help='Framework to use (will show available options if not specified)')
@click.option('--template', default=None, help='Template variant (will show available options if not specified)')
def init(folder, framework, template):
    """Initialize a new RunAgent project"""
    client = RunAgentClient(cli_mode=True)
    success = client.init(folder=folder, framework=framework, template=template)
    if not success:
        raise click.ClickException("Project initialization failed")

@click.command()
@click.option('--list', 'action_list', is_flag=True, help='List all available templates')
@click.option('--info', 'action_info', is_flag=True, help='Get detailed information about a specific template')
@click.option('--framework', help='Framework name (required for --info)')
@click.option('--template', help='Template name (required for --info)')
@click.option('--filter-framework', help='Filter templates by framework when listing')
@click.option('--format', type=click.Choice(['table', 'json', 'yaml']), default='table', help='Output format')
def template(action_list, action_info, framework, template, filter_framework, format):
    """Manage project templates - list available templates or get detailed information"""
    
    if not action_list and not action_info:
        click.echo("❌ Please specify either --list or --info")
        click.echo("Usage examples:")
        click.echo("  runagent template --list")
        click.echo("  runagent template --info --framework langchain --template basic")
        raise click.ClickException("No action specified")
    
    if action_list and action_info:
        click.echo("❌ Please specify only one action: --list or --info")
        raise click.ClickException("Multiple actions specified")
    
    client = RunAgentClient(cli_mode=True)
    
    if action_list:
        _handle_list_templates(client, filter_framework, format)
    elif action_info:
        _handle_template_info(client, framework, template)

def _handle_list_templates(client, filter_framework, format):
    """Handle the --list action"""
    try:
        available_templates = client.list_templates()
        
        if not available_templates:
            click.echo("❌ No templates available")
            return
        
        # Apply framework filter if specified
        if filter_framework:
            if filter_framework not in available_templates:
                click.echo(f"❌ Framework '{filter_framework}' not found")
                click.echo(f"Available frameworks: {', '.join(available_templates.keys())}")
                return
            available_templates = {filter_framework: available_templates[filter_framework]}
        
        # Output in different formats
        if format == 'json':
            import json
            click.echo(json.dumps(available_templates, indent=2))
        elif format == 'yaml':
            try:
                import yaml
                click.echo(yaml.dump(available_templates, default_flow_style=False))
            except ImportError:
                click.echo("❌ PyYAML not installed. Using JSON format instead.")
                import json
                click.echo(json.dumps(available_templates, indent=2))
        else:  # table format (default)
            click.secho("📋 Available Templates:", fg='cyan', bold=True)
            
            for framework_name, templates in available_templates.items():
                click.secho(f"\n🎯 {framework_name}:", fg='blue', bold=True)
                for tmpl in templates:
                    click.echo(f"  - {tmpl}")
            
            click.echo(f"\n💡 Use 'runagent template --info --framework <framework> --template <template>' for details")
            
    except Exception as e:
        click.echo(f"❌ Error listing templates: {str(e)}")

def _handle_template_info(client, framework, template):
    """Handle the --info action"""
    if not framework or not template:
        click.echo("❌ Both --framework and --template are required for --info")
        click.echo("Usage: runagent template --info --framework <framework> --template <template>")
        raise click.ClickException("Missing required parameters")
    
    try:
        from runagent.constants import TEMPLATE_REPO_URL, TEMPLATE_BRANCH, TEMPLATE_PREPATH
        from runagent.client.template_downloader import TemplateDownloader
        
        downloader = TemplateDownloader(TEMPLATE_REPO_URL, TEMPLATE_BRANCH)
        info = downloader.get_template_info(TEMPLATE_PREPATH, framework, template)
        
        if info:
            click.secho(f"📋 Template Information: {framework}/{template}", fg='cyan', bold=True)
            click.echo(f"Framework: {info['framework']}")
            click.echo(f"Template: {info['template']}")
            
            if 'metadata' in info:
                metadata = info['metadata']
                if 'description' in metadata:
                    click.echo(f"Description: {metadata['description']}")
                if 'requirements' in metadata:
                    click.echo(f"Requirements: {', '.join(metadata['requirements'])}")
                if 'version' in metadata:
                    click.echo(f"Version: {metadata['version']}")
                if 'author' in metadata:
                    click.echo(f"Author: {metadata['author']}")
            
            click.echo(f"\n📁 Structure:")
            click.echo(f"Files: {', '.join(info['files'])}")
            if info['directories']:
                click.echo(f"Directories: {', '.join(info['directories'])}")
            
            if 'readme' in info:
                click.echo(f"\n📖 README:")
                click.echo("-" * 50)
                click.echo(info['readme'])
                click.echo("-" * 50)
            
            click.echo(f"\n🚀 To use this template:")
            click.echo(f"runagent init --framework {framework} --template {template}")
            
        else:
            click.echo(f"❌ Template '{framework}/{template}' not found")
            
            # Suggest available templates for the framework
            try:
                available_templates = client.list_templates()
                if framework in available_templates:
                    click.echo(f"Available templates for {framework}: {', '.join(available_templates[framework])}")
                else:
                    click.echo(f"Available frameworks: {', '.join(available_templates.keys())}")
            except:
                pass
            
    except Exception as e:
        click.echo(f"❌ Error getting template info: {str(e)}")
