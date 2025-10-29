# runagent/client/template_downloader.py

import os
import shutil
import tempfile
import typing as t
from pathlib import Path
import requests

import git
from git import Repo
from runagent.utils.agent import validate_agent


class TemplateDownloadError(Exception):
    """Exception raised when template download fails"""
    pass


class TemplateDownloader:
    """Download templates from git repository with sparse checkout"""

    def __init__(self, repo_url: str, branch: str = "main"):
        '''
        Initialize template downloader

        Args:
            repo_url: Git repository URL
            branch: Branch to download from
        '''
        self.repo_url = repo_url
        self.branch = branch
        
        # Extract GitHub owner/repo for API usage
        self.github_token = os.getenv("GITHUB_TOKEN")
        if "github.com" in self.repo_url:
            parts = self.repo_url.replace(".git", "").split("/")
            self.github_owner = parts[-2]
            self.github_repo = parts[-1]
            self.use_github_api = True
        else:
            self.use_github_api = False
    
    def _github_api_get(self, path: str) -> dict:
        """
        Make a GET request to GitHub API
        
        Args:
            path: API path (e.g., "repos/owner/repo/contents/path")
            
        Returns:
            JSON response
        """
        url = f"https://api.github.com/{path}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        params = {"ref": self.branch}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403 and "rate limit" in response.text.lower():
            raise TemplateDownloadError(
                "GitHub API rate limit exceeded. Set GITHUB_TOKEN environment variable for higher limits."
            )
        else:
            raise TemplateDownloadError(
                f"GitHub API request failed: {response.status_code} - {response.text}"
            )
    
    def _download_github_folder_api(self, folder_path: str, local_dir: Path) -> None:
        """
        Download a folder from GitHub using API (much faster than git clone)
        
        Args:
            folder_path: Path to folder in repo (e.g., "templates/letta/default")
            local_dir: Local directory to save files
        """
        api_path = f"repos/{self.github_owner}/{self.github_repo}/contents/{folder_path}"
        
        try:
            contents = self._github_api_get(api_path)
        except TemplateDownloadError:
            # Fall back to git clone if API fails
            raise
        
        # Create local directory
        local_dir.mkdir(parents=True, exist_ok=True)
        
        for item in contents:
            if item['type'] == 'file':
                # Download file directly
                file_response = requests.get(item['download_url'], timeout=30)
                
                if file_response.status_code == 200:
                    local_file_path = local_dir / item['name']
                    local_file_path.write_bytes(file_response.content)
                else:
                    raise TemplateDownloadError(f"Failed to download file: {item['name']}")
                    
            elif item['type'] == 'dir':
                # Recursively download subdirectory
                sub_folder = local_dir / item['name']
                self._download_github_folder_api(item['path'], sub_folder)
    
    def _list_github_folder_api(self, folder_path: str) -> list:
        """
        List contents of a folder on GitHub using API (instant vs cloning)
        
        Args:
            folder_path: Path to folder in repo
            
        Returns:
            List of items in the folder
        """
        api_path = f"repos/{self.github_owner}/{self.github_repo}/contents/{folder_path}"
        return self._github_api_get(api_path)
    
    def _list_templates_via_api(self, prepath: str, framework_filter: str = None, debug_enabled: bool = False) -> t.Dict[str, t.List[str]]:
        """
        List templates using GitHub API (much faster than git clone!)
        
        Args:
            prepath: Pre-path before framework directory
            framework_filter: Optional specific framework to scan
            debug_enabled: Whether to log debug information
            
        Returns:
            Dictionary mapping framework names to list of template names
        """
        import time
        import logging
        logger = logging.getLogger(__name__)
        
        start_time = time.time()
        if debug_enabled:
            logger.info(f"[PERF] Using GitHub API to list templates")
        
        templates = {}
        
        # If framework filter specified, only scan that framework
        if framework_filter:
            framework_path = f"{prepath}/{framework_filter}" if prepath else framework_filter
            try:
                if debug_enabled:
                    logger.info(f"[PERF] Fetching templates for {framework_filter} via API")
                
                items = self._list_github_folder_api(framework_path)
                templates[framework_filter] = []
                
                for item in items:
                    if item['type'] == 'dir' and not item['name'].startswith('.'):
                        # Check if it has a config file (validate it's a template)
                        template_name = item['name']
                        try:
                            config_check_path = f"{framework_path}/{template_name}"
                            template_contents = self._list_github_folder_api(config_check_path)
                            
                            # Check if runagent.config.json exists
                            has_config = any(
                                f['name'] in ['runagent.config.json', 'runagent.config.yaml', 'runagent.config.yml']
                                for f in template_contents
                            )
                            
                            if has_config:
                                templates[framework_filter].append(template_name)
                                if debug_enabled:
                                    logger.debug(f"[PERF]   ✓ {template_name} valid")
                        except Exception as e:
                            if debug_enabled:
                                logger.debug(f"[PERF]   ✗ {template_name} skipped: {e}")
                
                api_time = time.time() - start_time
                if debug_enabled:
                    logger.info(f"[PERF] API listing completed in {api_time:.2f}s - found {len(templates[framework_filter])} templates")
                
                return templates
                
            except Exception as e:
                raise TemplateDownloadError(f"Failed to list templates via API: {e}")
        
        # Scan all frameworks
        try:
            if debug_enabled:
                logger.info(f"[PERF] Fetching all frameworks via API")
            
            framework_items = self._list_github_folder_api(prepath if prepath else "")
            
            for framework_item in framework_items:
                if framework_item['type'] == 'dir' and not framework_item['name'].startswith('.'):
                    framework_name = framework_item['name']
                    templates[framework_name] = []
                    
                    # List templates in this framework
                    try:
                        framework_path = f"{prepath}/{framework_name}" if prepath else framework_name
                        template_items = self._list_github_folder_api(framework_path)
                        
                        for template_item in template_items:
                            if template_item['type'] == 'dir' and not template_item['name'].startswith('.'):
                                template_name = template_item['name']
                                try:
                                    # Quick validation: check if config exists
                                    template_contents = self._list_github_folder_api(f"{framework_path}/{template_name}")
                                    has_config = any(
                                        f['name'] in ['runagent.config.json', 'runagent.config.yaml', 'runagent.config.yml']
                                        for f in template_contents
                                    )
                                    
                                    if has_config:
                                        templates[framework_name].append(template_name)
                                except Exception:
                                    pass  # Skip invalid templates
                    except Exception:
                        pass  # Skip frameworks with errors
            
            api_time = time.time() - start_time
            if debug_enabled:
                logger.info(f"[PERF] API listing completed in {api_time:.2f}s")
            
            return templates
            
        except Exception as e:
            raise TemplateDownloadError(f"Failed to list all templates via API: {e}")
 
    def download_template(
        self, prepath: str, framework: str, template: str, target_folder: str
    ) -> None:
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

        # Use GitHub API if available (much faster!)
        if self.use_github_api:
            try:
                self._download_github_folder_api(template_path, target_dir)
                return
            except Exception as e:
                # Fall back to git clone if API fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"GitHub API download failed, falling back to git clone: {e}")

        # Fallback: Use git clone with sparse checkout
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # Clone with sparse checkout for efficiency
                repo = Repo.clone_from(
                    self.repo_url,
                    temp_path,
                    branch=self.branch,
                    multi_options=[
                        "--filter=blob:none",  # Partial clone
                        "--no-checkout",  # Don't checkout initially
                    ],
                )

                # Configure sparse checkout
                repo.config_writer().set_value(
                    "core", "sparseCheckout", "true"
                ).release()

                # Create sparse-checkout file
                sparse_checkout_file = temp_path / ".git" / "info" / "sparse-checkout"
                sparse_checkout_file.parent.mkdir(exist_ok=True, parents=True)

                with open(sparse_checkout_file, "w") as f:
                    f.write(f"{template_path}/*\n")

                # Checkout the specified branch with sparse checkout
                repo.git.checkout(self.branch)

                # Copy template contents to target directory
                template_source_dir = temp_path / template_path

                if not template_source_dir.exists():
                    raise TemplateDownloadError(
                        f"Template '{template_path}' not found in repository branch '{self.branch}'"
                    )

                # Copy all contents (including agent.py, main.py, requirements.txt, .env, etc.)
                self._copy_directory_contents(template_source_dir, target_dir)

                # Verify essential files exist
                essential_files = ["runagent.config.json"]
                missing_files = []
                for file in essential_files:
                    if not (target_dir / file).exists():
                        missing_files.append(file)

                if missing_files:
                    raise TemplateDownloadError(
                        f"Template is missing essential files: {missing_files}"
                    )

            except git.exc.GitCommandError as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                raise TemplateDownloadError(f"Git error: {e}")
            except FileNotFoundError as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                raise TemplateDownloadError(str(e))
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
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

    def _scan_framework_templates(self, framework_dir: Path, template_list: list, debug_enabled: bool = False):
        """
        Helper to scan templates in a framework directory.
        
        Args:
            framework_dir: Path to framework directory
            template_list: List to append valid template names to
            debug_enabled: Whether to log debug information
        """
        import time
        import logging
        logger = logging.getLogger(__name__)
        
        for template_dir in framework_dir.iterdir():
            if template_dir.is_dir() and not template_dir.name.startswith("."):
                # Verify this is a valid template
                # Skip templates that fail validation (e.g., test directories without config)
                template_name = template_dir.name
                try:
                    validate_start = time.time()
                    if debug_enabled:
                        logger.debug(f"[PERF]   Validating template: {template_name}")
                    is_valid, _ = validate_agent(template_dir)
                    validate_time = time.time() - validate_start
                    
                    if is_valid:
                        if debug_enabled:
                            logger.debug(f"[PERF]   ✓ {template_name} valid ({validate_time:.3f}s)")
                        template_list.append(template_name)
                    else:
                        if debug_enabled:
                            logger.debug(f"[PERF]   ✗ {template_name} invalid ({validate_time:.3f}s)")
                except Exception as e:
                    if debug_enabled:
                        validate_time = time.time() - validate_start
                        logger.debug(f"[PERF]   ✗ {template_name} error ({validate_time:.3f}s): {e}")
                    # Skip invalid templates silently (e.g., test dirs, incomplete templates)
                    pass
    
    def list_available_templates(self, prepath: str, framework_filter: str = None) -> t.Dict[str, t.List[str]]:
        """
        List all available templates in the repository

        Args:
            prepath: Pre-path before framework directory
            framework_filter: Optional specific framework to scan (much faster)

        Returns:
            Dictionary mapping framework names to list of template names

        Raises:
            TemplateDownloadError: If listing fails
        """
        import time
        import logging
        import os
        logger = logging.getLogger(__name__)
        
        # Only show debug info if explicitly enabled
        debug_enabled = os.getenv('RUNAGENT_DEBUG') == '1'
        
        # Use GitHub API if available (much faster!)
        if self.use_github_api:
            try:
                return self._list_templates_via_api(prepath, framework_filter, debug_enabled)
            except TemplateDownloadError as e:
                if debug_enabled:
                    logger.warning(f"[PERF] GitHub API failed, falling back to git clone: {e}")
                # Fall through to git clone method
        
        # Fallback: Use git clone method
        with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # Shallow clone for listing
                start_time = time.time()
                if debug_enabled:
                    logger.info(f"[PERF] Starting git clone from {self.repo_url}")
                
                repo = Repo.clone_from(
                    self.repo_url, temp_path, branch=self.branch, depth=1
                )
                
                clone_time = time.time() - start_time
                if debug_enabled:
                    logger.info(f"[PERF] Git clone completed in {clone_time:.2f}s")
                
                templates = {}

                # Navigate to the prepath directory
                scan_start = time.time()
                prepath_dir = temp_path / prepath if prepath else temp_path

                if not prepath_dir.exists():
                    raise TemplateDownloadError(
                        f"Pre-path '{prepath}' not found in repository branch '{self.branch}'"
                    )

                # If framework filter specified, only scan that framework's directory
                if framework_filter:
                    if debug_enabled:
                        logger.info(f"[PERF] Scanning framework: {framework_filter}")
                    framework_dir = prepath_dir / framework_filter
                    if framework_dir.exists() and framework_dir.is_dir():
                        templates[framework_filter] = []
                        fw_start = time.time()
                        self._scan_framework_templates(framework_dir, templates[framework_filter], debug_enabled)
                        fw_time = time.time() - fw_start
                        if debug_enabled:
                            logger.info(f"[PERF] Scanned {framework_filter} in {fw_time:.2f}s - found {len(templates[framework_filter])} templates")
                    return templates

                # Scan all framework directories
                for framework_dir in prepath_dir.iterdir():
                    if framework_dir.is_dir() and not framework_dir.name.startswith("."):
                        framework_name = framework_dir.name
                        if debug_enabled:
                            logger.info(f"[PERF] Scanning framework: {framework_name}")
                        templates[framework_name] = []
                        fw_start = time.time()
                        self._scan_framework_templates(framework_dir, templates[framework_name], debug_enabled)
                        fw_time = time.time() - fw_start
                        if debug_enabled:
                            logger.info(f"[PERF] Scanned {framework_name} in {fw_time:.2f}s - found {len(templates[framework_name])} templates")

                scan_time = time.time() - scan_start
                if debug_enabled:
                    logger.info(f"[PERF] Total scanning time: {scan_time:.2f}s")
                return templates

            except git.exc.GitCommandError as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                
                raise TemplateDownloadError(f"Git error while listing templates: {e}")
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                raise TemplateDownloadError(f"Error listing templates: {e}")

    def get_template_info(
        self, prepath: str, framework: str, template: str
    ) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get information about a specific template (e.g., README, metadata)

        Args:
            prepath: Pre-path before framework directory
            framework: Framework name
            template: Template name

        Returns:
            Template metadata if available, None otherwise
        """
        template_path = f"{prepath}/{framework}/{template}" if framework else f"{prepath}/{template}"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # Clone with sparse checkout for the specific template
                repo = Repo.clone_from(
                    self.repo_url,
                    temp_path,
                    branch=self.branch,
                    multi_options=["--filter=blob:none", "--no-checkout"],
                )

                repo.config_writer().set_value(
                    "core", "sparseCheckout", "true"
                ).release()

                sparse_checkout_file = temp_path / ".git" / "info" / "sparse-checkout"
                sparse_checkout_file.parent.mkdir(exist_ok=True, parents=True)

                with open(sparse_checkout_file, "w") as f:
                    f.write(f"{template_path}/*\n")

                repo.git.checkout(self.branch)

                template_source_dir = temp_path / template_path

                if not template_source_dir.exists():
                    return None

                # Collect template information
                info = {
                    "framework": framework,
                    "template": template,
                    "files": [
                        f.name for f in template_source_dir.iterdir() if f.is_file()
                    ],
                    "directories": [
                        d.name for d in template_source_dir.iterdir() if d.is_dir()
                    ],
                }

                # Check for README
                readme_files = ["README.md", "README.txt", "readme.md", "readme.txt"]
                for readme_file in readme_files:
                    readme_path = template_source_dir / readme_file
                    if readme_path.exists():
                        info["readme"] = readme_path.read_text(encoding="utf-8")
                        break

                # Check for template.json metadata
                metadata_path = template_source_dir / "template.json"
                if metadata_path.exists():
                    import json

                    try:
                        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                        info["metadata"] = metadata
                    except json.JSONDecodeError:
                        if os.getenv('DISABLE_TRY_CATCH'):
                            raise
                        pass

                # Verify this is a valid template
                required_files = ["main.py", "agent.py"]
                info["valid"] = all(
                    (template_source_dir / f).exists() for f in required_files
                )

                return info

            except Exception:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                return None
