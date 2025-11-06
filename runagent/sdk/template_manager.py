"""
Template management for the SDK.
"""
import os
import shutil
import subprocess
import typing as t
from pathlib import Path

from ..constants import TEMPLATE_BRANCH, TEMPLATE_PREPATH, TEMPLATE_REPO_URL
from .exceptions import ValidationError
from .template_downloader import TemplateDownloader
from ..utils.agent import get_agent_config


class TemplateManager:
    """Manage project templates"""

    def __init__(self):
        """Initialize template manager"""
        self.downloader = TemplateDownloader(
            repo_url=TEMPLATE_REPO_URL, branch=TEMPLATE_BRANCH
        )

    def check_connectivity(self) -> bool:
        """Check if template repository is accessible using git ls-remote (lightweight approach)"""
        # Check if git is available before shelling out
        if not shutil.which("git"):
            raise RuntimeError("git is not installed or not found in PATH. Please install git to use template features.")
        
        try:
            # Use git ls-remote to check repository accessibility without cloning
            # This is much faster than the previous approach of calling list_available()
            result = subprocess.run(
                ["git", "ls-remote", "--heads", self.downloader.repo_url, self.downloader.branch],
                capture_output=True,
                text=True,
                timeout=10,  # 10 second timeout
                check=True
            )
            # Check if the branch exists in the remote repository
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return False

    def list_available(
        self, framework_filter: t.Optional[str] = None
    ) -> t.Dict[str, t.List[str]]:
        """
        List available templates.

        Args:
            framework_filter: Optional framework to filter by

        Returns:
            Dictionary mapping framework names to template lists
        """
        try:
            # Pass framework_filter to downloader for faster scanning
            templates = self.downloader.list_available_templates(
                TEMPLATE_PREPATH, 
                framework_filter=framework_filter
            )

            return templates
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
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
            return self.downloader.get_template_info(
                TEMPLATE_PREPATH, framework, template
            )
        except Exception:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return None

    def init_template(
        self, folder_path: Path, framework: str, template: str, overwrite: bool = False
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
        # Validate template exists - only fetch for this specific framework
        available_templates = self.list_available(framework_filter=framework)

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
        if folder_path.exists() and any(folder_path.iterdir()):
            if not overwrite:
                raise FileExistsError(
                    f"Folder '{folder_path}' already exists and is not empty. "
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
                target_folder=str(folder_path),
            )

            # Create project configuration
            self._create_project_config(folder_path)

            return True

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            # Clean up on failure
            # if folder_path.exists():
            #     import shutil

            #     shutil.rmtree(folder_path)
            raise ValidationError(f"Project initialization failed: {str(e)}")

    def _create_project_config(self, folder_path: Path):
        """Create project configuration file"""
        import time

        from ..utils.config import Config

        existing_config = get_agent_config(folder_path)

        existing_config.agent_name = folder_path.name
        existing_config.created_at = time.strftime("%Y-%m-%d %H:%M:%S")

        config_content = existing_config.model_dump(
            exclude={"agent_architecture", "framework"}
        )

        Config.create_config(str(folder_path), config_content)
