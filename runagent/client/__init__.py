"""
RunAgent client for deploying and managing AI agents.
"""
import os
import time
import click
import inquirer
import typing as t
from pathlib import Path
from runagent.constants import (
    TemplateVariant, Framework, TEMPLATE_REPO_URL,
    TEMPLATE_PREPATH, TEMPLATE_BRANCH
)
from runagent.client.template_downloader import TemplateDownloader
from runagent.utils.config import Config
from runagent.client.http import EndpointHandler
from runagent.utils.enums import ResponseStatus
from rich.table import Table
from rich.console import Console

# Console for pretty printing
console = Console()

_valid_keys: t.Set[str] = set()
_clients: t.List["RunAgentClient"] = []


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class ClientError(Exception):
    """Raised when client operations fail"""
    pass


class RunAgentClient:
    """Client for interacting with the RunAgent service."""

    def __init__(
        self,
        cli_mode: t.Optional[bool] = False,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None
    ):
        """Initialize RunAgent client with proper error handling"""
        
        self.cli_mode = cli_mode
        
        # Get configuration with fallbacks
        self.api_key = api_key or Config.get_api_key()
        self.base_url = base_url or Config.get_base_url()
        
        # Initialize endpoint handler
        self.endpoint_handler = EndpointHandler(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # Add to global clients list
        _clients.append(self)
        
        # If in CLI mode and not configured, show helpful message
        if cli_mode and not self.is_authenticated():
            if not api_key:  # Only show if not explicitly passed
                click.echo(
                    "⚠️  RunAgent is not configured. "
                    "Run 'runagent setup --api-key <key>' to get started."
                )

    def is_authenticated(self) -> bool:
        """Check if client has valid authentication"""
        return bool(self.api_key)

    def require_authentication(self, cli_mode: bool = None):
        """Ensure client is authenticated, raise error if not"""
        if cli_mode is None:
            cli_mode = self.cli_mode
            
        if not self.is_authenticated():
            error_msg = "Not authenticated. Run 'runagent setup --api-key <key>' to configure RunAgent."
            if cli_mode:
                raise click.ClickException(f"❌ {error_msg}")
            else:
                raise AuthenticationError(error_msg)


    def validate_connection(self) -> bool:
        """Validate current connection without raising exceptions"""
        if not self.is_authenticated():
            return False
        
        try:
            response = self.endpoint_handler.validate_api_key()
            return response.get("status") == ResponseStatus.SUCCESS.value
        except Exception:
            return False

    def setup(
        self,
        base_url: str = None,
        api_key: str = None,
        force: bool = False,
        cli_mode: bool = None
    ):
        """Configure RunAgent CLI settings with enhanced validation
        
        Args:
            base_url: API base URL
            api_key: API key for authentication
            force: Force reconfiguration even if already configured
            cli_mode: Enable interactive prompts (None = use instance default)
        """
        # Use instance cli_mode if not explicitly provided
        if cli_mode is None:
            cli_mode = self.cli_mode
        
        # Check if already configured and not forcing
        if not force and Config.is_configured():
            current_config = Config.get_user_config()
            
            if cli_mode:
                click.echo("⚠️  RunAgent is already configured:")
                click.echo(
                    f"   Base URL: {current_config.get('base_url', 'Not set')}"
                )
                click.echo(
                    f"   User: {current_config.get('email', 'Unknown')}"
                )
                
                if not click.confirm("Do you want to reconfigure?"):
                    return True
            else:
                # In SDK mode, just return success if already configured
                return True
        
        # Handle base URL
        base_url = base_url or Config.get_base_url()
        if base_url:
            # Validate URL format
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
            
            Config.set_base_url(base_url)
            if cli_mode:
                click.echo("✓ Base URL saved successfully!")
        
        # Validate API key is provided
        if not api_key:
            if cli_mode:
                click.echo("❌ API key is required for setup")
            raise ValueError("API key is required for setup")
        
        # Test connection before saving
        if cli_mode:
            click.echo(f"🔗 Testing connection to {base_url}...")
        
        # Create temporary endpoint handler for validation
        temp_handler = EndpointHandler(api_key=api_key, base_url=base_url)
        
        try:
            response = temp_handler.validate_api_key()
            
            if response.get("status") == ResponseStatus.ERROR.value:
                error_msg = "Authentication failed. Please check your API key"
                if cli_mode:
                    click.echo(f"❌ {error_msg}")
                else:
                    raise AuthenticationError(error_msg)
                return False
            
            # Only save if validation succeeds
            Config.set_api_key(api_key)
            if cli_mode:
                click.echo("✓ API key saved successfully!")
            
            # Update client instance
            self.api_key = api_key
            self.base_url = base_url
            self.endpoint_handler = EndpointHandler(
                api_key=api_key,
                base_url=base_url
            )
            
            if cli_mode:
                click.echo("✅ API key validation successful!")
            
            # Display and save user info
            if "data" in response and "user" in response["data"]:
                user = response["data"]["user"]
                
                if cli_mode:
                    table = Table(title="User Information")
                    table.add_column("Field", style="cyan")
                    table.add_column("Value", style="green")

                    for key, value in user.items():
                        table.add_row(key, str(value))
                        Config.set_user_config(key, value)
                    console.print(table)
                else:
                    # In SDK mode, just save the config silently
                    for key, value in user.items():
                        Config.set_user_config(key, value)
            
            return True
            
        except (ConnectionError, AuthenticationError, ClientError) as e:
            error_msg = f"Setup failed: {str(e)}"
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise  # Re-raise the original exception for SDK mode
            return False
        except Exception as e:
            error_msg = f"Unexpected error during setup: {str(e)}"
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise  # Re-raise for SDK mode
            return False

    def teardown(self, confirm: bool = False, cli_mode: bool = None):
        """Remove all RunAgent configuration and cached data
        
        Args:
            confirm: Skip confirmation prompt if True
            cli_mode: Enable interactive prompts (None = use instance default)
        """
        # Use instance cli_mode if not explicitly provided
        if cli_mode is None:
            cli_mode = self.cli_mode
        
        if not confirm and cli_mode:
            current_config = Config.get_user_config()
            if current_config:
                click.echo("📋 Current configuration:")
                click.echo(
                    f"   Base URL: {current_config.get('base_url', 'Not set')}"
                )
                click.echo(
                    f"   User: {current_config.get('email', 'Unknown')}"
                )
                click.echo(
                    f"   API Key: {'*' * 8}..."
                    f"{current_config.get('api_key', '')[-4:] if current_config.get('api_key') else 'Not set'}"
                )
            
            if not click.confirm(
                "⚠️  This will remove all RunAgent configuration. Continue?"
            ):
                if cli_mode:
                    click.echo("Teardown cancelled.")
                return False
        
        try:
            # Clear all user configuration
            if Config.clear_user_config() and cli_mode:
                click.echo("✓ User configuration removed")
            
            # Clear any deployment info in current directory
            deployments_dir = Path.cwd() / ".deployments"
            if deployments_dir.exists():
                import shutil
                shutil.rmtree(deployments_dir)
                if cli_mode:
                    click.echo("✓ Local deployment cache cleared")
            
            # Reset client instance
            self.api_key = None
            self.base_url = Config.get_base_url()  # Will fall back to default
            self.endpoint_handler = EndpointHandler(
                api_key=None,
                base_url=self.base_url
            )
            
            if cli_mode:
                click.echo("✅ RunAgent teardown completed successfully!")
                click.echo(
                    "💡 Run 'runagent setup --api-key <key>' to reconfigure"
                )
            
            return True
            
        except Exception as e:
            error_msg = f"Error during teardown: {str(e)}"
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise  # Re-raise for SDK mode
            return False

    def init(
        self,
        framework: str,
        template: str,
        folder: str = None,
        cli_mode: bool = None
    ):
        """🚀 Initialize a new RunAgent project with framework selection
        
        Args:
            framework: Framework to use (required)
            template: Template variant (required)
            folder: Project folder name
            cli_mode: Enable interactive prompts (None = use instance default)
        """
        # Use instance cli_mode if not explicitly provided
        if cli_mode is None:
            cli_mode = self.cli_mode
        
        # Check authentication first
        self.require_authentication(cli_mode=cli_mode)
        
        if cli_mode:
            click.secho(
                "🚀 Initializing RunAgent project...",
                fg='cyan',
                bold=True
            )
            click.secho("🔐 Checking authentication...", fg='yellow')
        
        # Validate connection
        if not self.validate_connection():
            error_msg = "Authentication validation failed"
            if cli_mode:
                click.echo(f"❌ {error_msg}")
                click.echo(
                    "💡 Run 'runagent setup --api-key <key>' to reconfigure"
                )
            else:
                raise AuthenticationError(error_msg)
            return False
        
        if cli_mode:
            with click.progressbar(range(5), label='🔄 Authenticating') as bar:
                for _ in bar:
                    time.sleep(0.2)
            click.secho("✅ Authentication successful!\n", fg='green')
        
        # Handle folder name
        if not folder:
            if cli_mode:
                folder = click.prompt(
                    "📁 Project folder name",
                    default=os.path.basename(os.getcwd())
                )
            else:
                # Use current directory name as default
                folder = os.path.basename(os.getcwd())
        
        project_dir = Path.cwd() / folder
        
        # Check if folder already exists and handle appropriately
        if project_dir.exists() and any(project_dir.iterdir()):
            if cli_mode:
                if not click.confirm(
                    f"⚠️  Folder '{folder}' already exists and is not empty. "
                    "Continue?"
                ):
                    click.echo("Project initialization cancelled.")
                    return False
            else:
                raise ValueError(
                    f"Folder '{folder}' already exists and is not empty"
                )
        
        project_dir.mkdir(parents=True, exist_ok=True)
        print(">>>", framework, ">>>", template)
        # Get available templates from repository
        try:
            available_templates = self._get_available_templates(
                cli_mode=cli_mode
            )
        except Exception as e:
            error_msg = f"Failed to fetch available templates: {str(e)}"
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise RuntimeError(error_msg)
            return False

        # Handle framework selection
        selected_framework = self._select_framework(
            framework,
            available_templates,
            cli_mode=cli_mode
        )
        if not selected_framework:
            return False

        # Handle template selection  
        selected_template = self._select_template(
            template,
            available_templates,
            selected_framework,
            cli_mode=cli_mode
        )
        if not selected_template:
            return False

        if cli_mode:
            click.secho(
                f"\n🛠️  Selected framework: {selected_framework} "
                f"({selected_template})\n",
                fg='magenta',
                bold=True
            )

        # Download and generate template files
        return self._download_and_setup_template(
            project_dir,
            selected_framework,
            selected_template,
            folder,
            cli_mode=cli_mode
        )

    def _get_available_templates(self, cli_mode: bool = False):
        """Fetch available templates from the git repository"""
        if cli_mode:
            click.echo("📋 Fetching available templates...")
        
        downloader = TemplateDownloader(
            repo_url=TEMPLATE_REPO_URL,
            branch=TEMPLATE_BRANCH
        )
        
        try:
            templates = downloader.list_available_templates(TEMPLATE_PREPATH)
            if cli_mode:
                click.echo("✅ Templates fetched successfully")
            return templates
        except Exception as e:
            if cli_mode:
                click.echo(f"❌ Error fetching templates: {str(e)}")
            raise

    def _select_framework(
        self,
        framework: str,
        available_templates: dict,
        cli_mode: bool = False
    ) -> str:
        """Select framework with validation against available templates"""
        
        # Validate framework
        if framework not in available_templates:
            error_msg = (
                f"Framework '{framework}' not available. "
                f"Available: {list(available_templates.keys())}"
            )
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise ValueError(error_msg)
            return None
        return framework
        
        # Interactive selection for CLI mode
        if cli_mode:
            frameworks = list(available_templates.keys())
            framework_choices = [
                (
                    f"{'🧠' if 'langchain' in fw.lower() else '🔧' if 'langgraph' in fw.lower() else '📜' if 'flask' in fw.lower() else '⚙️'} "
                    f"{fw}"
                )
                for fw in frameworks
            ]

            click.secho("🎯 Select a framework using arrow keys:", fg='blue')
            questions = [
                inquirer.List(
                    'framework',
                    message="",
                    choices=framework_choices,
                    carousel=True
                )
            ]
            answers = inquirer.prompt(questions)
            
            if not answers:  # User cancelled
                return None
                
            return answers['framework'].split(' ', 1)[1]  # Extract framework name
        else:
            # SDK mode: use provided framework
            return framework

    def _select_template(
        self,
        template: str,
        available_templates: dict,
        framework: str,
        cli_mode: bool = False
    ) -> str:
        """Select template with validation against available templates"""
        
        framework_templates = available_templates.get(framework, [])
        
        # Validate template
        if template not in framework_templates:
            error_msg = (
                f"Template '{template}' not available for framework "
                f"'{framework}'. Available: {framework_templates}"
            )
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise ValueError(error_msg)
            return None
        return template
        
        # Interactive selection for CLI mode
        if cli_mode:
            template_choices = [f"🔰 {tmpl}" for tmpl in framework_templates]

            click.secho(
                "\n🧱 Select template type using arrow keys:",
                fg='blue'
            )
            questions = [
                inquirer.List(
                    'template',
                    message="",
                    choices=template_choices,
                    carousel=True
                )
            ]
            answers = inquirer.prompt(questions)
            
            if not answers:  # User cancelled
                return None
                
            return answers['template'].split(' ', 1)[1]  # Extract template name
        else:
            # SDK mode: use provided template
            return template

    def _download_and_setup_template(
        self,
        project_dir: Path,
        framework: str,
        template: str,
        folder: str,
        cli_mode: bool = False
    ):
        """Download template from git repository and set up the project"""
        
        try:
            if cli_mode:
                click.secho("📦 Downloading project template...", fg='cyan')
            
            # Initialize template downloader
            downloader = TemplateDownloader(
                repo_url=TEMPLATE_REPO_URL,
                branch=TEMPLATE_BRANCH
            )
            
            # Download template to project directory
            downloader.download_template(
                prepath=TEMPLATE_PREPATH,
                framework=framework,
                template=template,
                target_folder=str(project_dir)
            )
            
            # Create project configuration
            config_content = {
                "project_name": folder,
                "framework": framework,
                "template": template,
                "version": "0.1.0",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "template_source": {
                    "repo_url": TEMPLATE_REPO_URL,
                    "branch": TEMPLATE_BRANCH,
                    "path": f"{TEMPLATE_PREPATH}/{framework}/{template}"
                }
            }
            Config.create_config(project_dir, config_content)
            
            if cli_mode:
                click.secho(
                    f"✅ Successfully initialized RunAgent project in "
                    f"📁 {folder}\n",
                    fg='green',
                    bold=True
                )
                
                # List created files
                click.secho("🗂️  Files created:", fg='cyan')
                for file_path in project_dir.rglob('*'):
                    if (
                        file_path.is_file()
                        and not file_path.name.startswith('.')
                    ):
                        relative_path = file_path.relative_to(project_dir)
                        click.echo(f"  - {relative_path}")

                click.secho("\n📝 Next steps:", fg='yellow')
                click.echo(
                    "  1️⃣  Edit the configuration files to customize your agent"
                )
                click.echo("  2️⃣  Update your API keys in `.env` (if present)")
                click.echo(
                    f"  3️⃣  Run 'runagent deploy --folder {folder}' "
                    "to deploy your agent 🚀"
                )
            
            return True

        except Exception as e:
            error_msg = f"Error setting up project: {str(e)}"
            if cli_mode:
                click.secho(f"❌ {error_msg}", fg='red', err=True)
            else:
                raise RuntimeError(error_msg)
            return False

    def list_templates(self, cli_mode: bool = None):
        """List all available templates from the repository
        
        Args:
            cli_mode: Enable pretty printing (None = use instance default)
        """
        if cli_mode is None:
            cli_mode = self.cli_mode
        
        try:
            available_templates = self._get_available_templates(
                cli_mode=cli_mode
            )
            
            if cli_mode:
                click.secho("📋 Available Templates:", fg='cyan', bold=True)
                
                for framework, templates in available_templates.items():
                    click.secho(f"\n🎯 {framework}:", fg='blue', bold=True)
                    for template in templates:
                        click.echo(f"  - {template}")
            
            return available_templates
            
        except Exception as e:
            error_msg = f"Failed to list templates: {str(e)}"
            if cli_mode:
                click.echo(f"❌ {error_msg}")
            else:
                raise RuntimeError(error_msg)
            return None

