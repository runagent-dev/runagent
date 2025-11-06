import click
import typing as t
from runagent.utils.enums.framework import Framework
from rich.console import Console

console = Console()

# Auto-generate Click options from enum
def add_framework_options(func):
    """Decorator to automatically add framework options from enum"""
    selectable_frameworks = Framework.get_selectable_frameworks()
    
    # Add options in reverse order (Click processes them backwards)
    for framework in reversed(selectable_frameworks):
        option_name = f"--{framework.value}"
        help_text = f"Use {framework.value.upper()} framework"
        func = click.option(option_name, is_flag=True, help=help_text)(func)
    
    return func


# Helper function to extract selected framework from kwargs
def get_selected_framework(kwargs: dict) -> t.Optional[Framework]:
    """Extract the selected framework from click kwargs"""
    selectable_frameworks = Framework.get_selectable_frameworks()
    
    selected_frameworks = [
        framework for framework in selectable_frameworks 
        if kwargs.get(framework.value, False)
    ]
    
    if len(selected_frameworks) > 1:
        framework_names = [f"--{fw.value}" for fw in selected_frameworks]
        raise click.UsageError(
            f"Only one framework can be specified. Found: {', '.join(framework_names)}"
        )
    
    return selected_frameworks[0] if selected_frameworks else None


def safe_prompt(questions, cancellation_message="[dim]Operation cancelled.[/dim]"):
    """
    Wrapper around inquirer.prompt() that handles ESC key and KeyboardInterrupt gracefully.
    
    Args:
        questions: List of inquirer questions
        cancellation_message: Message to display when cancelled (default: "[dim]Operation cancelled.[/dim]")
    
    Returns:
        Dictionary of answers if successful, None if cancelled
    """
    import inquirer
    
    try:
        answers = inquirer.prompt(questions)
        if not answers:
            console.print(cancellation_message)
            return None
        return answers
    except KeyboardInterrupt:
        # Handle Ctrl+C
        console.print(f"\n{cancellation_message}")
        return None
    except EOFError:
        # Handle EOF (sometimes raised by ESC in some terminals)
        console.print(f"\n{cancellation_message}")
        return None