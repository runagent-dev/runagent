# runagent/client/sdk.py (UPDATED - Fix run_agent error handling)
"""
Main SDK class that provides all RunAgent functionality.
"""

import os
import time
import typing as t
from pathlib import Path

from runagent.sdk.server.local_server import LocalServer
from runagent.utils.agent import detect_framework, validate_agent

from .config import SDKConfig
from .db import DBService
from .deployment import RemoteDeployment
from .exceptions import AuthenticationError, ValidationError
from .template_manager import TemplateManager


class RunAgentSDK:
    """
    Main RunAgent SDK class providing all functionality for agent deployment and management.
    """

    def __init__(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        config_file: t.Optional[str] = None,
    ):
        """
        Initialize the RunAgent SDK.

        Args:
            api_key: API key for authentication (can also be set via RUNAGENT_API_KEY env var)
            base_url: Base URL for the RunAgent service (can also be set via RUNAGENT_BASE_URL env var)
            config_file: Path to configuration file (optional)
        """
        # Initialize configuration
        self.config = SDKConfig(
            api_key=api_key, base_url=base_url, config_file=config_file
        )

        # Initialize managers
        self.templates = TemplateManager()
        self.db_service = DBService()
        # self.local = LocalDeployment(self.config)
        self.remote = RemoteDeployment(self.config)

        # Validate configuration on initialization
        self._validate_basic_setup()

    def _validate_basic_setup(self):
        """Validate basic SDK setup"""

        # Check if we can access template repository
        try:
            self.templates.check_connectivity()
        except Exception as e:
            # Non-fatal warning for template connectivity
            pass

    # Configuration Methods
    def configure(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        save: bool = True,
    ) -> bool:
        """
        Configure the SDK with authentication and server details.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the RunAgent service
            save: Whether to save configuration to disk

        Returns:
            True if configuration is successful

        Raises:
            AuthenticationError: If authentication fails
        """
        return self.config.setup(
            api_key=api_key, base_url=base_url, save=save, validate_auth=True
        )

    def configure_basic(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        save: bool = True,
    ) -> bool:
        """
        Configure the SDK without validating authentication (for testing/development).

        Args:
            api_key: API key for authentication
            base_url: Base URL for the RunAgent service
            save: Whether to save configuration to disk

        Returns:
            True if configuration is successful
        """
        return self.config.setup(
            api_key=api_key, base_url=base_url, save=save, validate_auth=False
        )

    def is_configured(self) -> bool:
        """Check if SDK is properly configured"""
        return self.config.is_configured()

    def get_config_status(self) -> t.Dict[str, t.Any]:
        """Get detailed configuration status"""
        return self.config.get_status()

    # Template Methods
    def list_templates(
        self, framework: t.Optional[str] = None
    ) -> t.Dict[str, t.List[str]]:
        """
        List available project templates.

        Args:
            framework: Optional framework filter

        Returns:
            Dictionary mapping framework names to template lists
        """
        return self.templates.list_available(framework_filter=framework)

    def get_template_info(
        self, framework: str, template: str
    ) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get detailed information about a specific template.

        Args:
            framework: Framework name (e.g., 'langchain', 'langgraph')
            template: Template name (e.g., 'basic', 'advanced')

        Returns:
            Template information dictionary or None if not found
        """
        return self.templates.get_info(framework, template)

    # Project Initialization Methods
    def init_project(
        self,
        folder: str,
        framework: str = "langchain",
        template: str = "basic",
        overwrite: bool = False,
    ) -> bool:
        """
        Initialize a new agent project.

        Args:
            folder: Project folder name
            framework: Framework to use (langchain, langgraph, llamaindex)
            template: Template variant (basic, advanced)
            overwrite: Whether to overwrite existing folder

        Returns:
            True if initialization is successful

        Raises:
            ValidationError: If parameters are invalid
            FileExistsError: If folder exists and overwrite is False
        """
        return self.templates.init_project(
            folder=folder, framework=framework, template=template, overwrite=overwrite
        )

    def list_local_agents(self) -> t.List[t.Dict[str, t.Any]]:
        """List all locally deployed agents"""
        return self.local.list_agents()

    def get_local_capacity(self) -> t.Dict[str, t.Any]:
        """Get local database capacity information"""
        return self.local.get_capacity_info()

    def serve_local_agent(
        self,
        agent_path: Path,
        port: int = 8450,
        host: str = "127.0.0.1",
        debug: bool = False,
    ) -> None:
        """
        Start thxe local FastAPI server for testing agents.

        Args:
            port: Port to run server on
            host: Host to bind to
            debug: Enable debug mode
        """
        is_valid, details = validate_agent(agent_path)
        if not is_valid:
            raise ValidationError(details["error_msgs"][0])

        server = LocalServer.from_path(agent_path, port, host)
        server.start(debug=debug)

    # Remote Deployment Methods
    def deploy_remote(
        self,
        folder: str,
        framework: t.Optional[str] = None,
        config: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> t.Dict[str, t.Any]:
        """
        Deploy an agent to the remote server (upload + start).

        Args:
            folder: Folder containing agent files
            framework: Framework type (auto-detected if not specified)
            config: Optional deployment configuration

        Returns:
            Deployment result with agent_id and endpoint

        Raises:
            AuthenticationError: If not properly authenticated
        """
        self._require_authentication()
        return self.remote.deploy_agent(
            folder_path=folder, framework=framework, config=config
        )

    def upload_agent(
        self, folder: str, framework: t.Optional[str] = None
    ) -> t.Dict[str, t.Any]:
        """
        Upload an agent to the remote server (without starting).

        Args:
            folder: Folder containing agent files
            framework: Framework type (auto-detected if not specified)

        Returns:
            Upload result with agent_id

        Raises:
            AuthenticationError: If not properly authenticated
        """
        self._require_authentication()
        return self.remote.upload_agent(folder_path=folder, framework=framework)

    def start_remote_agent(
        self, agent_id: str, config: t.Optional[t.Dict[str, t.Any]] = None
    ) -> t.Dict[str, t.Any]:
        """
        Start a previously uploaded agent on the remote server.

        Args:
            agent_id: ID of the uploaded agent
            config: Optional deployment configuration

        Returns:
            Start result with endpoint

        Raises:
            AuthenticationError: If not properly authenticated
        """
        self._require_authentication()
        return self.remote.start_agent(agent_id, config)

    def get_agent_info(self, agent_id: str, local: bool = True) -> t.Dict[str, t.Any]:
        """
        Get comprehensive information about an agent.

        Args:
            agent_id: Agent identifier
            local: Whether to check local or remote agents

        Returns:
            Agent information dictionary
        """
        if local:
            return self.local.get_agent_info(agent_id)
        else:
            self._require_authentication()
            return self.remote.get_agent_info(agent_id)

    def delete_agent(self, agent_id: str, local: bool = True) -> t.Dict[str, t.Any]:
        """
        Delete an agent (files only for local, full deletion for remote).

        Args:
            agent_id: Agent identifier
            local: Whether to delete local or remote agent

        Returns:
            Deletion result
        """
        if local:
            return self.local.delete_agent(agent_id)
        else:
            self._require_authentication()
            return self.remote.delete_agent(agent_id)

    # Utility Methods
    def run_agent(
        self,
        agent_id: str,
        message: t.Optional[str] = None,
        messages: t.Optional[t.List[t.Dict[str, str]]] = None,
        config: t.Optional[t.Dict[str, t.Any]] = None,
        local: bool = True,
    ) -> t.Dict[str, t.Any]:
        """
        Run an agent with a message or conversation.

        Args:
            agent_id: Agent identifier
            message: Simple message string
            messages: List of message objects with 'role' and 'content'
            config: Optional configuration
            local: Whether to run locally or remotely

        Returns:
            Agent execution result with proper error handling
        """
        # Prepare input data
        if messages:
            input_data = {"messages": messages}
        elif message:
            input_data = {"messages": [{"role": "user", "content": message}]}
        else:
            raise ValidationError("Either 'message' or 'messages' must be provided")

        if config:
            input_data["config"] = config

        # Run the agent
        if local:
            result = self.local.run_agent(agent_id, input_data)

            # Enhanced error handling for local agents
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")

                # If error is None or empty, try to get more details
                if not error_msg or error_msg == "None":
                    # Try to get agent info to see what's wrong
                    agent_info = self.get_agent_info(agent_id, local=True)
                    if agent_info.get("success"):
                        agent_data = agent_info["agent_info"]
                        if not agent_data.get("deployment_exists"):
                            result["error"] = (
                                f"Agent {agent_id} deployment files not found"
                            )
                        elif not agent_data.get("source_exists"):
                            result["error"] = f"Agent {agent_id} source files not found"
                        elif agent_data.get("status") == "error":
                            result["error"] = f"Agent {agent_id} is in error state"
                        else:
                            result["error"] = (
                                f"Agent {agent_id} execution failed with unknown error"
                            )
                    else:
                        result["error"] = f"Agent {agent_id} not found in database"

                # Add suggestions based on error type
                result["suggestions"] = self._get_error_suggestions(result["error"])

            return result
        else:
            self._require_authentication()
            return self.remote.run_agent(agent_id, input_data)

    def _get_error_suggestions(self, error_msg: str) -> t.List[str]:
        """Get suggestions based on error message"""
        suggestions = []

        if "not found" in error_msg.lower():
            suggestions.append("Check if the agent ID is correct")
            suggestions.append("Use sdk.list_local_agents() to see available agents")

        if "deployment files not found" in error_msg.lower():
            suggestions.append("Try redeploying the agent")
            suggestions.append("Check if the deployment directory exists")

        if "error state" in error_msg.lower():
            suggestions.append("Check agent logs for details")
            suggestions.append("Try redeploying the agent")

        if "execution failed" in error_msg.lower():
            suggestions.append("Check if all dependencies are installed")
            suggestions.append("Verify the agent's main.py file is valid")
            suggestions.append("Check environment variables (.env file)")

        return suggestions

    def detect_framework(self, folder: str) -> str:
        """
        Auto-detect the framework used in an agent project.

        Args:
            folder: Path to agent folder

        Returns:
            Detected framework name
        """
        return detect_framework(folder)

    # Database and Server Management
    def cleanup_local_database(self, days_old: int = 30) -> t.Dict[str, t.Any]:
        """
        Clean up old local database records.

        Args:
            days_old: Delete records older than this many days

        Returns:
            Cleanup result
        """
        return self.local.cleanup_old_records(days_old)

    def get_local_stats(self) -> t.Dict[str, t.Any]:
        """Get local database statistics"""
        return self.local.get_database_stats()

    # Debug Methods
    def debug_agent(self, agent_id: str, local: bool = True) -> t.Dict[str, t.Any]:
        """
        Debug an agent to identify issues.

        Args:
            agent_id: Agent identifier
            local: Whether to debug local or remote agent

        Returns:
            Debug information
        """
        if not local:
            return {"error": "Remote agent debugging not yet implemented"}

        # Get agent info
        agent_info = self.get_agent_info(agent_id, local=True)
        if not agent_info.get("success"):
            return {"error": f"Agent {agent_id} not found"}

        agent_data = agent_info["agent_info"]
        debug_info = {
            "agent_id": agent_id,
            "status": agent_data.get("status"),
            "framework": agent_data.get("framework"),
            "deployment_exists": agent_data.get("deployment_exists"),
            "source_exists": agent_data.get("source_exists"),
            "deployment_path": agent_data.get("deployment_path"),
            "source_path": agent_data.get("folder_path"),
            "stats": agent_data.get("stats", {}),
            "issues": [],
        }

        # Check for common issues
        if not agent_data.get("deployment_exists"):
            debug_info["issues"].append("Deployment files missing")

        if not agent_data.get("source_exists"):
            debug_info["issues"].append("Source files missing")

        if agent_data.get("stats", {}).get("success_rate", 0) == 0:
            debug_info["issues"].append("Agent has never run successfully")

        # Try to run the agent directly and capture the error
        try:
            result = self.run_local_agent_direct(
                agent_id, {"messages": [{"role": "user", "content": "test"}]}
            )
            if not result.get("success"):
                debug_info["last_error"] = result.get("error")
                debug_info["traceback"] = result.get("traceback")
        except Exception as e:
            debug_info["direct_run_error"] = str(e)

        return debug_info

    # Private Helper Methods
    def _require_authentication(self):
        """Ensure SDK is properly authenticated for remote operations"""
        if not self.config.is_authenticated():
            raise AuthenticationError(
                "Remote operations require authentication. "
                "Call sdk.configure(api_key='your-key') first."
            )

    def _validate_folder_path(self, folder: str) -> Path:
        """Validate and return folder path"""
        folder_path = Path(folder)
        if not folder_path.exists():
            raise ValidationError(f"Folder not found: {folder}")
        return folder_path

    # Context Manager Support
    def __enter__(self):
        """Enter context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - cleanup if needed"""
        pass

    # String representation
    def __repr__(self):
        return f"RunAgentSDK(configured={self.is_configured()})"
