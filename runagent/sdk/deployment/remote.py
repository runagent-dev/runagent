"""
Remote deployment management.
"""

import typing as t
from pathlib import Path

from ..exceptions import AuthenticationError, ValidationError
from ..rest_client import RestClient


class RemoteDeployment:
    """Manage remote agent deployments"""

    def __init__(self, config):
        """
        Initialize remote deployment manager.

        Args:
            config: SDK configuration object
        """
        self.config = config
        self.client = RestClient(base_url=config.base_url, api_key=config.api_key)

    def deploy_agent(
        self,
        folder_path: str,
        framework: t.Optional[str] = None,
        config: t.Optional[t.Dict[str, t.Any]] = None,
    ) -> t.Dict[str, t.Any]:
        """
        Deploy an agent remotely (upload + start).

        Args:
            folder_path: Path to agent folder
            framework: Framework type (auto-detected if None)
            config: Optional deployment configuration

        Returns:
            Deployment result
        """
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise ValidationError(f"Folder not found: {folder_path}")

        # Auto-detect framework if not provided
        if not framework:
            framework = self._detect_framework(folder_path)

        metadata = {"framework": framework}

        return self.client.deploy_agent(folder_path=str(folder_path), metadata=metadata)

    def upload_agent(
        self, folder_path: str, framework: t.Optional[str] = None
    ) -> t.Dict[str, t.Any]:
        """
        Upload an agent without starting it.

        Args:
            folder_path: Path to agent folder
            framework: Framework type (auto-detected if None)

        Returns:
            Upload result
        """
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise ValidationError(f"Folder not found: {folder_path}")

        # Auto-detect framework if not provided
        if not framework:
            framework = self._detect_framework(folder_path)

        metadata = {"framework": framework}

        return self.client.upload_agent(folder_path=str(folder_path), metadata=metadata)

    def start_agent(
        self, agent_id: str, config: t.Optional[t.Dict[str, t.Any]] = None
    ) -> t.Dict[str, t.Any]:
        """
        Start a previously uploaded agent.

        Args:
            agent_id: ID of uploaded agent
            config: Optional deployment configuration

        Returns:
            Start result
        """
        return self.client.start_agent(agent_id, config or {})

    def get_agent_info(self, agent_id: str) -> t.Dict[str, t.Any]:
        """Get information about a remote agent"""
        return self.client.get_agent_status(agent_id)

    def run_agent(
        self, agent_id: str, input_data: t.Dict[str, t.Any]
    ) -> t.Dict[str, t.Any]:
        """Run a remote agent"""
        # This would need to be implemented in RestClient
        # For now, return a placeholder
        return {"success": False, "error": "Remote agent execution not yet implemented"}

    def delete_agent(self, agent_id: str) -> t.Dict[str, t.Any]:
        """Delete a remote agent"""
        # This would need to be implemented in RestClient
        # For now, return a placeholder
        return {"success": False, "error": "Remote agent deletion not yet implemented"}

    def _detect_framework(self, folder_path: Path) -> str:
        """Auto-detect framework from project files"""
        # Same logic as LocalDeployment
        framework_keywords = {
            "langgraph": ["langgraph", "StateGraph", "Graph"],
            "langchain": ["langchain", "ConversationChain", "AgentExecutor"],
            "llamaindex": ["llama_index", "VectorStoreIndex", "QueryEngine"],
        }

        for file_to_check in ["main.py", "agent.py"]:
            file_path = folder_path / file_to_check
            if file_path.exists():
                try:
                    content = file_path.read_text().lower()
                    for framework, keywords in framework_keywords.items():
                        if any(keyword.lower() in content for keyword in keywords):
                            return framework
                except:
                    continue

        # Check requirements.txt
        req_file = folder_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text().lower()
                for framework, keywords in framework_keywords.items():
                    if any(keyword.lower() in content for keyword in keywords):
                        return framework
            except:
                pass

        return "unknown"
