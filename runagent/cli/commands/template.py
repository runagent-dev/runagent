import os
import click
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from enum import Enum

from runagent import RunAgent
from runagent.utils.enums import Framework


console = Console()

def create_templates_table(templates_data):
    """Create a rich table for templates display"""
    table = Table(
        title="🧱 Available Templates",
        show_header=True,
        header_style="bold cyan",
        border_style="blue"
    )
    
    table.add_column("Framework", style="magenta", width=12)
    table.add_column("Category", style="blue", width=10)
    table.add_column("Templates", style="yellow", min_width=20)
    table.add_column("Count", style="green", justify="center", width=8)
    
    # Sort frameworks for consistent display (by string value, not enum)
    sorted_frameworks = sorted(templates_data.keys(), key=str)
    
    for framework in sorted_frameworks:
        framework_name = framework.value
        template_list = templates_data[framework]
        
        # Get framework category if it's a valid framework
        framework_enum = Framework.validate_framework(framework_name) if Framework.is_valid_framework(framework_name) else None
        category = framework_enum.get_category() if framework_enum else "Unknown"
        
        # Format templates list
        if len(template_list) <= 3:
            templates_str = ", ".join(template_list)
        else:
            templates_str = f"{', '.join(template_list[:3])}... (+{len(template_list)-3} more)"
        
        table.add_row(
            framework_name,
            category,
            templates_str,
            str(len(template_list))
        )
    
    return table


@click.command()
@click.option(
    "--list", "action_list", is_flag=True, help="List all available templates"
)
@click.option(
    "--info", "action_info", is_flag=True, help="Get detailed template information"
)
@click.option("--framework", help="Framework name (required for --info)")
@click.option("--template", help="Template name (required for --info)")
@click.option("--filter-framework", help="Filter templates by framework")
@click.option(
    "--format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def template(action_list, action_info, framework, template, filter_framework, format):
    """Manage project templates"""

    if not action_list and not action_info:
        console.print(
            "❌ Please specify either [cyan]--list[/cyan] or [cyan]--info[/cyan]"
        )
        raise click.ClickException("No action specified")

    try:
        sdk = RunAgent()

        if action_list:
            # Validate filter framework if provided
            if filter_framework and not Framework.validate_framework(filter_framework):
                available = [fw.value for fw in Framework.get_selectable_frameworks()]
                console.print(f"❌ [red]Invalid framework '{filter_framework}'[/red]")
                console.print(f"Available frameworks: {', '.join(available)}")
                raise click.ClickException("Invalid framework specified")
            
            templates = sdk.list_templates(framework=Framework.from_value(filter_framework))

            if format == "json":
                templates_json = {fw.value: templates[fw] for fw in templates}
                console.print(json.dumps(templates_json, indent=2))
            else:
                # Use rich table for better display
                if templates:
                    table = create_templates_table(templates)
                    console.print(table)
                    
                    # Show total count
                    total_templates = sum(len(tmpl_list) for tmpl_list in templates.values())
                    total_frameworks = len(templates)
                    
                    console.print(f"\n📊 [bold]Summary:[/bold] {total_frameworks} frameworks, {total_templates} templates total")
                else:
                    console.print("📋 [yellow]No templates found[/yellow]")

                # Show usage hint
                console.print(
                    f"\n💡 [dim]Use [cyan]'runagent template --info --framework <fw> --template <tmpl>'[/cyan] for details[/dim]"
                )

        elif action_info:
            if not framework or not template:
                console.print(
                    "❌ Both [cyan]--framework[/cyan] and [cyan]--template[/cyan] are required for --info"
                )
                raise click.ClickException("Missing required parameters")

            # Validate framework
            framework_enum = Framework.validate_framework(framework)
            if not framework_enum:
                available = [fw.value for fw in Framework.get_selectable_frameworks()]
                console.print(f"❌ [red]Invalid framework '{framework}'[/red]")
                console.print(f"Available frameworks: {', '.join(available)}")
                raise click.ClickException("Invalid framework specified")
            
            template_info = sdk.get_template_info(framework, template)

            if template_info:
                # Create a nice panel for template info
                info_content = []
                
                # Basic info
                info_content.append(f"[bold]Framework:[/bold] [magenta]{template_info['framework']}[/magenta]")
                info_content.append(f"[bold]Template:[/bold] [yellow]{template_info['template']}[/yellow]")
                
                if framework_enum:
                    info_content.append(f"[bold]Category:[/bold] [blue]{framework_enum.get_category()}[/blue]")
                
                # Metadata
                if "metadata" in template_info:
                    metadata = template_info["metadata"]
                    if "description" in metadata:
                        info_content.append(f"[bold]Description:[/bold] {metadata['description']}")
                    if "requirements" in metadata:
                        info_content.append(f"[bold]Requirements:[/bold] {', '.join(metadata['requirements'])}")

                # Structure
                info_content.append(f"\n[bold]📁 Structure:[/bold]")
                info_content.append(f"[dim]Files:[/dim] {', '.join(template_info['files'])}")
                if template_info.get("directories"):
                    info_content.append(f"[dim]Directories:[/dim] {', '.join(template_info['directories'])}")

                # Create panel
                panel = Panel(
                    "\n".join(info_content),
                    title=f"📋 Template: {framework}/{template}",
                    title_align="left",
                    border_style="cyan"
                )
                console.print(panel)

                # README section
                if "readme" in template_info:
                    readme_content = template_info["readme"]
                    if len(readme_content) > 500:
                        readme_content = readme_content[:500] + "..."
                    
                    readme_panel = Panel(
                        readme_content,
                        title="📖 README",
                        title_align="left",
                        border_style="yellow"
                    )
                    console.print(readme_panel)

                # Usage instructions
                console.print("\n🚀 [bold]To use this template:[/bold]")
                console.print(f"[cyan]runagent init --{framework} --template {template}[/cyan]")
                
            else:
                console.print(
                    f"❌ Template [yellow]{framework}/{template}[/yellow] not found"
                )

                # Show available templates for this framework
                templates = sdk.list_templates()
                if framework in templates:
                    available_templates = templates[framework]
                    console.print(f"\n📋 [bold]Available templates for {framework}:[/bold]")
                    for tmpl in available_templates:
                        console.print(f"  • {tmpl}")
                else:
                    # Show available frameworks
                    available_frameworks = Framework.get_all_values()
                    console.print(f"\n🎯 [bold]Available frameworks:[/bold]")
                    for fw in available_frameworks:
                        console.print(f"  • {fw}")

    except Exception as e:
        if os.getenv('DISABLE_TRY_CATCH'):
            raise
        console.print(f"❌ [red]Template error:[/red] {e}")
        raise click.ClickException("Template operation failed")