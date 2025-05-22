# runagent/client/template_downloader.py

import shutil
import tempfile
from pathlib import Path
import git
from git import Repo
import typing as t


class TemplateDownloadError(Exception):
    """Exception raised when template download fails"""
    pass


class TemplateDownloader:
    """Download templates from git repository with sparse checkout"""
    
    def __init__(self, repo_url: str, branch: str = 'main'):
        """
        Initialize template downloader
        
        Args:
            repo_url: Git repository URL
            branch: Branch to download from
        """
        self.repo_url = repo_url
        self.branch = branch
    
    def download_template(self, prepath: str, framework: str, template: str, target_folder: str) -> None:
        """
        Download template contents to target folder
        
        Args:
            prepath: Pre-path before framework directory
            framework: Framework type (e.g., 'langchain', 'langgraph')
            template: Template name (e.g., 'basic', 'advanced')
            target_folder: Local project folder path
            
        Raises:
            TemplateDownloadError: If download fails
        """
        template_path = f"{prepath}/{framework}/{template}"
        
        # Create target directory
        target_dir = Path(target_folder)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Use temporary directory for sparse checkout
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Clone with sparse checkout for efficiency
                repo = Repo.clone_from(
                    self.repo_url,
                    temp_path,
                    branch=self.branch,
                    multi_options=[
                        '--filter=blob:none',  # Partial clone
                        '--no-checkout'        # Don't checkout initially
                    ]
                )
                
                # Configure sparse checkout
                repo.config_writer().set_value("core", "sparseCheckout", "true").release()
                
                # Create sparse-checkout file
                sparse_checkout_file = temp_path / '.git' / 'info' / 'sparse-checkout'
                sparse_checkout_file.parent.mkdir(exist_ok=True, parents=True)
                
                with open(sparse_checkout_file, 'w') as f:
                    f.write(f"{template_path}/*\n")
                
                # Checkout the specified branch with sparse checkout
                repo.git.checkout(self.branch)
                
                # Copy template contents to target directory
                template_source_dir = temp_path / template_path
                
                if not template_source_dir.exists():
                    raise TemplateDownloadError(
                        f"Template '{template_path}' not found in repository branch '{self.branch}'"
                    )
                
                # Copy all contents
                self._copy_directory_contents(template_source_dir, target_dir)
                
            except git.exc.GitCommandError as e:
                raise TemplateDownloadError(f"Git error: {e}")
            except FileNotFoundError as e:
                raise TemplateDownloadError(str(e))
            except Exception as e:
                raise TemplateDownloadError(f"Unexpected error: {e}")
    
    def _copy_directory_contents(self, source_dir: Path, target_dir: Path) -> None:
        """
        Copy all contents from source directory to target directory
        Preserves directory structure but not the parent directory itself
        """
        for item in source_dir.iterdir():
            target_item = target_dir / item.name
            
            if item.is_dir():
                # Recursively copy directory
                shutil.copytree(item, target_item, dirs_exist_ok=True)
            else:
                # Copy file
                shutil.copy2(item, target_item)
    
    def list_available_templates(self, prepath: str) -> t.Dict[str, t.List[str]]:
        """
        List all available templates in the repository
        
        Args:
            prepath: Pre-path before framework directory
            
        Returns:
            Dictionary mapping framework names to list of template names
            
        Raises:
            TemplateDownloadError: If listing fails
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Shallow clone for listing
                repo = Repo.clone_from(
                    self.repo_url,
                    temp_path,
                    branch=self.branch,
                    depth=1
                )
                
                templates = {}
                
                # Navigate to the prepath directory
                prepath_dir = temp_path / prepath if prepath else temp_path
                
                if not prepath_dir.exists():
                    raise TemplateDownloadError(
                        f"Pre-path '{prepath}' not found in repository branch '{self.branch}'"
                    )
                
                # Scan for framework directories
                for framework_dir in prepath_dir.iterdir():
                    if framework_dir.is_dir() and not framework_dir.name.startswith('.'):
                        framework_name = framework_dir.name
                        templates[framework_name] = []
                        
                        # Scan for template directories
                        for template_dir in framework_dir.iterdir():
                            if template_dir.is_dir() and not template_dir.name.startswith('.'):
                                templates[framework_name].append(template_dir.name)
                
                return templates
                
            except git.exc.GitCommandError as e:
                raise TemplateDownloadError(f"Git error while listing templates: {e}")
            except Exception as e:
                raise TemplateDownloadError(f"Error listing templates: {e}")
    
    def get_template_info(self, prepath: str, framework: str, template: str) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get information about a specific template (e.g., README, metadata)
        
        Args:
            prepath: Pre-path before framework directory
            framework: Framework name
            template: Template name
            
        Returns:
            Template metadata if available, None otherwise
        """
        template_path = f"{prepath}/{framework}/{template}"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Clone with sparse checkout for the specific template
                repo = Repo.clone_from(
                    self.repo_url,
                    temp_path,
                    branch=self.branch,
                    multi_options=['--filter=blob:none', '--no-checkout']
                )
                
                repo.config_writer().set_value("core", "sparseCheckout", "true").release()
                
                sparse_checkout_file = temp_path / '.git' / 'info' / 'sparse-checkout'
                sparse_checkout_file.parent.mkdir(exist_ok=True, parents=True)
                
                with open(sparse_checkout_file, 'w') as f:
                    f.write(f"{template_path}/*\n")
                
                repo.git.checkout(self.branch)
                
                template_source_dir = temp_path / template_path
                
                if not template_source_dir.exists():
                    return None
                
                # Look for metadata files
                info = {
                    'framework': framework,
                    'template': template,
                    'files': [f.name for f in template_source_dir.iterdir() if f.is_file()],
                    'directories': [d.name for d in template_source_dir.iterdir() if d.is_dir()]
                }
                
                # Check for README
                readme_files = ['README.md', 'README.txt', 'readme.md', 'readme.txt']
                for readme_file in readme_files:
                    readme_path = template_source_dir / readme_file
                    if readme_path.exists():
                        info['readme'] = readme_path.read_text(encoding='utf-8')
                        break
                
                # Check for template.json metadata
                metadata_path = template_source_dir / 'template.json'
                if metadata_path.exists():
                    import json
                    try:
                        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                        info['metadata'] = metadata
                    except json.JSONDecodeError:
                        pass
                
                return info
                
            except Exception:
                return None