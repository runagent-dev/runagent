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


def show_serve_progress(steps: list = None):
    """
    Show a subtle progress animation for server startup
    
    Args:
        steps: List of (message, completed) tuples showing progress steps
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.live import Live
    from rich.text import Text
    import time
    
    default_steps = [
        "Initializing server",
        "Loading agent configuration",
        "Setting up endpoints",
        "Starting FastAPI server",
    ]
    
    steps_to_show = steps if steps else default_steps
    total_steps = len(steps_to_show)
    
    # Create progress bar with RunAgent branding colors
    progress = Progress(
        SpinnerColumn(spinner_style="cyan"),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=30, style="cyan", complete_style="bold cyan"),
        TextColumn("[dim]{task.percentage:>3.0f}%[/dim]"),
        console=console,
        transient=True,  # This will auto-clear when done
    )
    
    with progress:
        task = progress.add_task("Starting server...", total=100)
        
        for i, step in enumerate(steps_to_show):
            # Update progress
            progress.update(task, description=f"[cyan]{step}...[/cyan]", completed=int((i + 1) / total_steps * 100))
            time.sleep(0.3)  # Brief pause for each step
        
        # Complete
        progress.update(task, completed=100, description="[bold green]Server ready![/bold green]")


def show_simple_serve_progress(message: str = "Starting server..."):
    """
    Show a simple, controlled progress indicator that doesn't clear terminal.
    Uses a spinner with RunAgent branding colors, then updates to static message.
    
    Args:
        message: Message to display
    """
    from rich.status import Status
    from rich.live import Live
    from rich.text import Text
    import time
    
    # Create status with RunAgent branding - use spinner name as string
    status = Status(
        f"[bold cyan]{message}[/bold cyan]",
        spinner="dots",
        console=console,
    )
    
    with Live(
        status,
        console=console,
        refresh_per_second=12,
        transient=False,  # Don't clear - convert to static message
    ) as live:
        # Show spinner for brief moment
        time.sleep(0.7)
        
        # Update to static completion message that stays visible
        # Clean up the message for completion display
        completion_text = message.replace("...", "").strip()
        if "ing " in completion_text:
            # Convert "Initializing" -> "Initialized", "Creating" -> "Created", etc.
            completion_text = completion_text.replace("ing ", "ed ")
        elif not completion_text.endswith("ed"):
            # Add "completed" if it doesn't end with past tense
            completion_text = f"{completion_text} completed"
        
        live.update(Text.from_markup(f"[bold green]✅ {completion_text}[/bold green]"))
        time.sleep(0.15)
