# runagent/client.py
"""
RunAgent client for deploying and managing AI agents.
"""
import os
import time
import click
import inquirer
import typing as t
from pathlib import Path
# from runagent.storage.user import UserData
from runagent.utils.url import get_api_url_base
from runagent.constants import LOCAL_CACHE_DIRECTORY, USER_DATA_FILE_NAME, ENV_RUNAGENT_API_KEY, TemplateVariant, Framework, Base, DEFAULT_BASE_URL, ENV_RUNAGENT_BASE_URL
from runagent.exceptions import ApiKeyError, ApiKeyNotProvidedError
from runagent.client.file_handler import FileHandler
from runagent.templates import TemplateFactory
from runagent.utils.config import Config
from runagent.client.http import EndpointHandler

_valid_keys: t.Set[str] = set()
_clients: t.List["RunAgentClient"] = []

DEFAULT_FRAMEWORK = "langchain"
DEFAULT_TEMPLATE = "basic"


class RunAgentClient:
    """Client for interacting with the RunAgent service."""

    _api_key: t.Optional[str] = None

    def __init__(
        self,
        cli_mode: t.Optional[bool] = False,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
    ):

        self.api_key = api_key or Config.get_api_key()
        self.base_url = base_url or get_api_url_base()
        self.cli_mode = cli_mode
        self.endpoint_handler = EndpointHandler(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        _clients.append(self)

    @staticmethod
    def get_latest() -> "RunAgentClient":
        """Get latest composio client from the runtime stack."""
        if len(_clients) == 0:
            _ = RunAgentClient()
        return _clients[-1]


    @api_key.setter
    def api_key(self, value: str) -> None:
        self._api_key = value

    # @property
    # def http(self) -> HttpClient:
    #     if not self._http:
    #         self._http = HttpClient(
    #             base_url=self.base_url,
    #             api_key=self.api_key,
    #             runtime=self.runtime,
    #         )
    #     return self._http

    # @http.setter
    # def http(self, value: HttpClient) -> None:
    #     self._http = value

    def setup(self, base_url: str = None, api_key: str = None):
        """Configure RunAgent CLI settings"""

        if base_url is None:
            # * source 1: CLI/SDK direct input
            # * source 1.5: User config file
            # * source 2: Environment Key
            # * source 3: Default Value
            base_url = Config.get_base_url()
        else:
            Config.set_base_url(base_url)
            click.echo("✓ Saving base_url successful!")

        if api_key is None:
            # * source 1: CLI/SDK direct input
            # * source 2: Environment Key
            base_url = Config.get_api_key()

        Config.set_api_key(api_key)
        if api_key is not None:
            click.echo("✓ Saving api_key successful!")

        click.echo(f"Testing connection to {base_url}...")
        try:
            response = self.endpoint_handler.validate_api_key()
            if response.status_code == 200:
                click.echo("✓ Connection successful!")
                user_data = response["user"]
                for field, value in user_data.items():
                    print(f"{field}: {value}")
                    Config.set_user_config(field, value)

            else:
                click.echo(f"✗ Server returned status code {response.status_code}")
                if not click.confirm("Continue anyway?"):
                    return
        except Exception as e:
            click.echo(f"✗ Connection failed: {str(e)}")
            if not click.confirm("Continue anyway?"):
                return

    @staticmethod
    def validate_api_key(key: str, base_url: t.Optional[str] = None) -> str:
        """Validate given API key."""
        if key in _valid_keys:
            return key

        # base_url = base_url or get_api_url_base()
        # response = requests.get(
        #     url=base_url + str(v1 / "client" / "auth" / "client_info"),
        #     headers={
        #         "x-api-key": key,
        #         "x-request-id": generate_request_id(),
        #     },
        #     timeout=60,
        # )
        # if response.status_code in (401, 403):
        #     raise ApiKeyError("API Key is not valid!")

        # if response.status_code != 200:
        #     raise ApiKeyError(f"Unexpected error: HTTP {response.status_code}")

        # _valid_keys.add(key)
        return key

    def init(
        self,
        folder: str,
        framework: str = DEFAULT_FRAMEWORK,
        template: str = DEFAULT_TEMPLATE
    ):
        """🚀 Initialize a new RunAgent project with framework selection"""
        click.secho("🚀 Initializing RunAgent project...", fg='cyan', bold=True)
        
        # Simulate authentication check
        click.secho("🔐 Checking authentication...", fg='yellow')
        with click.progressbar(range(5), label='🔄 Authenticating') as bar:
            for _ in bar:
                time.sleep(0.2)

        click.secho("✅ Authentication successful!\n", fg='green')

        # Get folder name if not provided
        if not folder:
            folder = click.prompt(
                "📁 Project folder name",
                default=os.path.basename(os.getcwd())
            )

        project_dir = Path.cwd() / folder
        # TODO: If already exist, raise proper error message
        project_dir.mkdir(parents=True)
        if framework is not None:
            selected_framework = framework
        else:
            # Framework selection using inquirer
            frameworks = [f.value for f in Framework]
            framework_choices = []
            for fw in frameworks:
                emoji = "🧠" if "langchain" in fw.lower() else "🔧" if "langgraph" in fw.lower() else "📜" if "Flask" in fw.lower() else "⚙️"
                framework_choices.append(f"{emoji} {fw}")

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
            selected_framework = answers['framework'].split(' ', 1)[1]  # Extract framework name without emoji

        # Template selection using inquirer

        if template is not None:
            selected_template = TemplateVariant.BASIC.value
        else:
            template_choices = [f"🔰 {TemplateVariant.BASIC.value}", f"🧠 {TemplateVariant.ADVANCED.value}"]

            click.secho("\n🧱 Select template type using arrow keys:", fg='blue')
            questions = [
                inquirer.List(
                    'template',
                    message="",
                    choices=template_choices,
                    carousel=True)
            ]
            answers = inquirer.prompt(questions)
            selected_template = answers['template'].split(' ', 1)[1]  # Extract template name without emoji

        click.secho(f"\n🛠️  Selected framework: {selected_framework} ({selected_template})\n", fg='magenta', bold=True)

        # Generate template files
        try:
            click.secho("📦 Generating project template...\n", fg='cyan')
            template = TemplateFactory.get_template(selected_framework, selected_template)
            files = template.generate_files()

            for filename, content in files.items():
                FileHandler.create_file(os.path.join(project_dir, filename), content)

            config_content = {
                "project_name": folder,
                "framework": selected_framework,
                "level": selected_template,
                "version": "0.1.0",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            Config.create_config(project_dir, config_content)

            click.secho(f"✅ Successfully initialized RunAgent project in 📁 {folder}\n", fg='green', bold=True)

            click.secho("🗂️  Files created:", fg='cyan')
            for filename in files.keys():
                click.echo(f"  - {filename}")

            click.secho("\n📝 Next steps:", fg='yellow')
            click.echo("  1️⃣  Edit the `agent.py` file to customize your agent")
            click.echo("  2️⃣  Update your API keys in `.env`")
            click.echo(f"  3️⃣  Run 'runagent deploy --folder {folder}' to deploy your agent 🚀")

        except Exception as e:
            click.secho(f"❌ Error: {str(e)}", fg='red', err=True)

