"""
Template management for the SDK.
"""

import typing as t
from pathlib import Path

from ..constants import (
    TEMPLATE_REPO_URL,
    TEMPLATE_BRANCH, 
    TEMPLATE_PREPATH
)
from .template_downloader import TemplateDownloader
from .exceptions import ValidationError


class TemplateManager:
    """Manage project templates"""
    
    def __init__(self):
        """Initialize template manager"""
        self.downloader = TemplateDownloader(
            repo_url=TEMPLATE_REPO_URL,
            branch=TEMPLATE_BRANCH
        )
    
    def check_connectivity(self) -> bool:
        """Check if template repository is accessible"""
        try:
            self.list_available()
            return True
        except Exception:
            return False
    
    def list_available(self, framework_filter: t.Optional[str] = None) -> t.Dict[str, t.List[str]]:
        """
        List available templates.
        
        Args:
            framework_filter: Optional framework to filter by
            
        Returns:
            Dictionary mapping framework names to template lists
        """
        try:
            templates = self.downloader.list_available_templates(TEMPLATE_PREPATH)
            
            if framework_filter:
                if framework_filter in templates:
                    return {framework_filter: templates[framework_filter]}
                else:
                    return {}
            
            return templates
        except Exception as e:
            raise ValidationError(f"Failed to fetch templates: {str(e)}")
    
    def get_info(self, framework: str, template: str) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get detailed information about a template.
        
        Args:
            framework: Framework name
            template: Template name
            
        Returns:
            Template information or None if not found
        """
        try:
            return self.downloader.get_template_info(TEMPLATE_PREPATH, framework, template)
        except Exception:
            return None
    
    def init_project(
        self,
        folder: str,
        framework: str,
        template: str,
        overwrite: bool = False
    ) -> bool:
        """
        Initialize a new project from template.
        
        Args:
            folder: Project folder name
            framework: Framework to use
            template: Template variant
            overwrite: Whether to overwrite existing folder
            
        Returns:
            True if successful
            
        Raises:
            ValidationError: If template is invalid
            FileExistsError: If folder exists and overwrite is False
        """
        # Validate template exists
        available_templates = self.list_available()
        if framework not in available_templates:
            raise ValidationError(
                f"Framework '{framework}' not available. "
                f"Available: {list(available_templates.keys())}"
            )
        
        if template not in available_templates[framework]:
            raise ValidationError(
                f"Template '{template}' not available for {framework}. "
                f"Available: {available_templates[framework]}"
            )
        
        # Check folder existence
        folder_path = Path(folder)
        if folder_path.exists() and any(folder_path.iterdir()):
            if not overwrite:
                raise FileExistsError(
                    f"Folder '{folder}' already exists and is not empty. "
                    "Use overwrite=True to force initialization."
                )
        
        # Create folder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Download template
            self.downloader.download_template(
                prepath=TEMPLATE_PREPATH,
                framework=framework,
                template=template,
                target_folder=str(folder_path)
            )
            
            # Create project configuration
            self._create_project_config(folder_path, framework, template)
            
            return True
            
        except Exception as e:
            # Clean up on failure
            if folder_path.exists():
                import shutil
                shutil.rmtree(folder_path)
            raise ValidationError(f"Project initialization failed: {str(e)}")
    
    def _create_project_config(self, folder_path: Path, framework: str, template: str):
        """Create project configuration file"""
        import time
        from ..utils.config import Config
        
        config_content = {
            "agent_name": folder_path.name,
            "framework": framework,
            "template": template,
            "version": "0.1.0",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "template_source": {
                "repo_url": TEMPLATE_REPO_URL,
                "branch": TEMPLATE_BRANCH,
                "path": f"{TEMPLATE_PREPATH}/{framework}/{template}"
            },
            "architecture": {
                "main_file": "main.py",
                "agent_file": "agent.py",
                "entry_point": "run"
            }
        }
        
        Config.create_config(str(folder_path), config_content)
