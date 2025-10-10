"""
CLI Branding - ASCII art logo and styling for RunAgent
"""

from rich.console import Console

console = Console()


def print_logo(show_tagline: bool = True, brand_color: str = "cyan"):
    """
    Print the RunAgent ASCII art logo
    "Run" in brand color (cyan), "Agent" in white
    
    Args:
        show_tagline: Whether to show the tagline below the logo
        brand_color: Brand color for "Run" part (default: cyan)
    """
    # Split logo into "Run" part (cyan) and "Agent" part (white)
    logo = f"""[dim]╔═══════════════════════════════════════════════════════════════╗
║                                                               ║[/dim]
[bold {brand_color}]║   ██████╗ ██╗   ██╗███╗   ██╗[/bold {brand_color}][bold white] █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/bold white]
[bold {brand_color}]║   ██╔══██╗██║   ██║████╗  ██║[/bold {brand_color}][bold white]██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/bold white]
[bold {brand_color}]║   ██████╔╝██║   ██║██╔██╗ ██║[/bold {brand_color}][bold white]███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   [/bold white]
[bold {brand_color}]║   ██╔══██╗██║   ██║██║╚██╗██║[/bold {brand_color}][bold white]██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   [/bold white]
[bold {brand_color}]║   ██║  ██║╚██████╔╝██║ ╚████║[/bold {brand_color}][bold white]██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   [/bold white]
[bold {brand_color}]║   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝[/bold {brand_color}][bold white]╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   [/bold white]
[dim]║                                                               ║
╚═══════════════════════════════════════════════════════════════╝[/dim]"""
    
    console.print(logo, highlight=False)
    
    if show_tagline:
        console.print(f"[dim]         Deploy and manage AI agents with ease 🚀[/dim]\n")


def print_compact_logo(brand_color: str = "cyan"):
    """
    Print a compact version of the RunAgent logo for smaller spaces
    "Run" in brand color, "Agent" in white
    
    Args:
        brand_color: Brand color for "Run" part (default: cyan)
    """
    logo = f"""
[bold {brand_color}]  ██████╗ ██╗   ██╗███╗   ██╗[/bold {brand_color}][bold white] █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/bold white]
[bold {brand_color}]  ██╔══██╗██║   ██║████╗  ██║[/bold {brand_color}][bold white]██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/bold white]
[bold {brand_color}]  ██████╔╝██║   ██║██╔██╗ ██║[/bold {brand_color}][bold white]███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   [/bold white]
[bold {brand_color}]  ██╔══██╗██║   ██║██║╚██╗██║[/bold {brand_color}][bold white]██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   [/bold white]
[bold {brand_color}]  ██║  ██║╚██████╔╝██║ ╚████║[/bold {brand_color}][bold white]██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   [/bold white]
[bold {brand_color}]  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝[/bold {brand_color}][bold white]╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   [/bold white]"""
    console.print(logo, highlight=False)


def print_minimal_logo(brand_color: str = "cyan"):
    """
    Print a minimal single-line logo
    "Run" in brand color, "Agent" in white
    
    Args:
        brand_color: Brand color for "Run" part (default: cyan)
    """
    console.print(f"[bold {brand_color}]Run[/bold {brand_color}][bold white]Agent[/bold white] [dim]|[/dim] [dim]Deploy AI agents with ease 🚀[/dim]")


def print_header(command_name: str = None, brand_color: str = "cyan"):
    """
    Print a simple header bar like a webpage header
    Perfect for internal pages without overwhelming the user
    
    Args:
        command_name: Optional command name to show (e.g., "Configuration", "Database")
        brand_color: Brand color for "Run" part (default: cyan)
    """
    # Top border
    console.print(f"[dim]{'─' * 70}[/dim]")
    
    # Header content
    if command_name:
        console.print(
            f"[bold {brand_color}]Run[/bold {brand_color}][bold white]Agent[/bold white] "
            f"[dim]›[/dim] {command_name}"
        )
    else:
        console.print(
            f"[bold {brand_color}]Run[/bold {brand_color}][bold white]Agent[/bold white] "
            f"[dim]CLI[/dim]"
        )
    
    # Bottom border
    console.print(f"[dim]{'─' * 70}[/dim]\n")


def print_welcome_banner(version: str = None):
    """
    Print a welcome banner with logo and version
    
    Args:
        version: Version string to display
    """
    print_logo(show_tagline=True, brand_color="cyan")
    
    if version:
        console.print(f"[dim]                          Version {version}[/dim]\n")
    else:
        console.print()


def print_setup_banner():
    """Print a special banner for the setup command"""
    print_logo(show_tagline=False, brand_color="cyan")
    console.print("[bold cyan]                    🎉 Welcome to RunAgent! 🎉[/bold cyan]")
    console.print("[dim]                Let's get you set up in a few steps...[/dim]\n")
