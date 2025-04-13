# runagent/templates/__init__.py
"""
Templates for agent initialization.
"""

import os
import shutil
import importlib.resources as pkg_resources
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_template_path(framework, template_name="default"):
    """
    Get the path to a template.
    
    Args:
        framework: Agent framework (e.g., "langgraph")
        template_name: Template name (e.g., "default", "advanced")
        
    Returns:
        Path to the template directory
    """
    template_dir = f"{framework}/{template_name}"
    return pkg_resources.files("runagent.templates").joinpath(template_dir)

def create_project_from_template(target_path, framework="langgraph", template_name="default"):
    """
    Create a new project from a template.
    
    Args:
        target_path: Path to create the project in
        framework: Agent framework (e.g., "langgraph")
        template_name: Template name (e.g., "default", "advanced")
        
    Returns:
        Path to the created project
    """
    template_path = get_template_path(framework, template_name)
    target_path = Path(target_path)
    
    # Ensure target directory exists
    os.makedirs(target_path, exist_ok=True)
    
    logger.debug(f"Creating project from template {framework}/{template_name} in {target_path}")
    
    # Copy template files
    for file in template_path.iterdir():
        if file.is_file():
            shutil.copy(file, target_path / file.name)
    
    # Create requirements.txt if it doesn't exist
    requirements_path = target_path / "requirements.txt"
    if not requirements_path.exists():
        with open(requirements_path, "w") as f:
            if framework == "langgraph":
                f.write("langgraph>=0.0.15\nlangchain>=0.0.191\n")
    
    return target_path

def list_templates():
    """
    List all available templates.
    
    Returns:
        Dict mapping framework names to lists of template names
    """
    templates = {}
    
    # Get templates root directory
    templates_root = pkg_resources.files("runagent.templates")
    
    # Iterate through frameworks
    for framework_dir in templates_root.iterdir():
        if framework_dir.is_dir():
            framework_name = framework_dir.name
            templates[framework_name] = []
            
            # Iterate through templates for this framework
            for template_dir in framework_dir.iterdir():
                if template_dir.is_dir():
                    templates[framework_name].append(template_dir.name)
    
    return templates