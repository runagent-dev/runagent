import os
import re

from runagent.sdk import RunAgentSDK
from runagent.sdk.rest_client import RestClient
from runagent.sdk.socket_client import SocketClient
from runagent.utils.serializer import CoreSerializer
from rich.console import Console
console = Console()


class RunAgentExecutionError(Exception):
    """Exception raised when a remote agent execution fails."""

    def __init__(self, code: str, message: str, suggestion: str | None = None, details: dict | None = None):
        self.code = code or "UNKNOWN_ERROR"
        self.message = message or "Unknown error"
        self.suggestion = suggestion
        self.details = details
        super().__init__(f"[{self.code}] {self.message}")


class RunAgentClient:

    def __init__(self, agent_id: str, entrypoint_tag: str, local: bool = True, host: str = None, port: int = None):
        self.sdk = RunAgentSDK()
        self.serializer = CoreSerializer()
        self.local = local
        self.agent_id = agent_id
        self.entrypoint_tag = entrypoint_tag
        
        # FIXED: Detect if this is a streaming entrypoint
        self.is_streaming = entrypoint_tag.endswith("_stream")

        if local:
            if host and port:
                agent_host = host
                agent_port = port
                console.print(f"🔌 [cyan]Using explicit address: {agent_host}:{agent_port}[/cyan]")
            else:
                agent_info = self.sdk.db_service.get_agent(agent_id)
                if not agent_info:
                    raise ValueError(f"Agent {agent_id} not found in local DB")

                self.agent_info = agent_info
                agent_host = self.agent_info["host"]
                agent_port = self.agent_info["port"]

                console.print(f"🔍 [cyan]Auto-resolved address for agent {agent_id}: {agent_host}:{agent_port}[/cyan]")

            agent_base_url_local = f"http://{agent_host}:{agent_port}"
            agent_socket_url_local = f"ws://{agent_host}:{agent_port}"

            self.rest_client = RestClient(base_url=agent_base_url_local)
            self.socket_client = SocketClient(base_socket_url=agent_socket_url_local)
        else:
            self.rest_client = RestClient(is_local=False)
            self.socket_client = SocketClient(is_local=False)

    def run(self, *input_args, **input_kwargs):
        """
        FIXED: Smart execution - automatically uses streaming or non-streaming based on entrypoint
        """
        # FIXED: If this is a streaming entrypoint, automatically use run_stream
        if self.is_streaming:
            console.print(f"[cyan]Detected streaming entrypoint, using WebSocket streaming[/cyan]")
            return self.run_stream(*input_args, **input_kwargs)
        
        # Non-streaming execution (HTTP POST)
        response = self.rest_client.run_agent(
            self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
        )
        # Only print debug response in DISABLE_TRY_CATCH mode
        if os.getenv('DISABLE_TRY_CATCH'):
            print(f"response: {response}")
        if response.get("success"):
            # Handle new response format with nested data
            if "data" in response and "result_data" in response["data"]:
                response_data = response["data"]["result_data"].get("data")
            else:
                # Fallback to old format for backward compatibility
                response_data = response.get("output_data")
            return self.serializer.deserialize_object(response_data)

        else:
            # Handle new error format with ErrorDetail object
            error_info = response.get("error")
            if isinstance(error_info, dict) and "message" in error_info:
                # New format with ErrorDetail object
                error_message = error_info.get("message", "Unknown error")
                error_code = error_info.get("code", "UNKNOWN_ERROR")
                suggestion = error_info.get("suggestion") or self._build_suggestion(error_code, error_message)
                raise RunAgentExecutionError(
                    code=error_code,
                    message=error_message,
                    suggestion=suggestion,
                    details=error_info.get("details"),
                )
            else:
                # Fallback to old format for backward compatibility
                raise self._build_error_from_string(response.get("error"))

    def run_stream(self, *input_args, **input_kwargs):
        """Stream agent execution results in real-time via WebSocket"""
        try:
            # FIXED: Return the generator directly, don't try to iterate here
            return self.socket_client.run_stream(
                self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
            )
        except Exception as e:
            # Handle streaming errors with proper formatting
            raise Exception(f"Streaming failed: {str(e)}")

    def _run_stream(self, *input_args, **input_kwargs):
        """Legacy method - use run_stream instead"""
        return self.run_stream(*input_args, **input_kwargs)

    def _build_suggestion(self, code: str, message: str) -> str | None:
        message_lower = (message or "").lower()

        if "not found" in message_lower:
            tag_match = re.search(r"['\"](?P<tag>[A-Za-z0-9_\-]+)['\"]", message or "") if "entrypoint" in message_lower else None
            dashboard_hint = f"https://app.run-agent.ai/dashboard/agents/{self.agent_id}"

            if tag_match:
                entrypoint = tag_match.group("tag")
                return (
                    f"Check that the entrypoint tag `{entrypoint}` exists for this agent. "
                    f"Update or redeploy the agent if needed, then verify in the dashboard: {dashboard_hint}."
                )

            return (
                "Verify the agent ID and ensure it is deployed. "
                f"If the agent was modified locally, redeploy it with `runagent deploy` or upload/start it again. "
                f"You can review its status in the dashboard: {dashboard_hint}."
            )

        if "must be deployed" in message_lower or "current status" in message_lower:
            return (
                "Deploy the agent before running it. "
                f"Use `runagent deploy` (or `runagent start --id {self.agent_id}` if already uploaded) and confirm its status in the RunAgent dashboard."
            )

        if code == "CONNECTION_ERROR":
            dashboard_hint = f"https://app.run-agent.ai/dashboard/agents/{self.agent_id}"
            return (
                "Check your network connection and confirm the RunAgent service URL is reachable. "
                f"If the problem persists, review the agent in the dashboard: {dashboard_hint}."
            )

        return None

    def _build_error_from_string(self, error_value) -> RunAgentExecutionError:
        if isinstance(error_value, RunAgentExecutionError):
            return error_value

        error_text = str(error_value) if error_value else "Unknown error"

        match = re.match(r"^\[(?P<code>[A-Z0-9_]+)]\s*(?P<message>.*)$", error_text)
        if match:
            code = match.group("code")
            message = match.group("message") or "Unknown error"
        else:
            code = "UNKNOWN_ERROR"
            message = error_text

        suggestion = self._build_suggestion(code, message)
        return RunAgentExecutionError(code=code, message=message, suggestion=suggestion)