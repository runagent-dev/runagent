import click
import typing as t
from runagent.utils.enums.framework import Framework

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
