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
        self.dashboard_url = f"https://app.run-agent.ai/dashboard/agents/{self.agent_id}"
        self.agent_host = None
        self.agent_port = None
        
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

            self.agent_host = agent_host
            self.agent_port = agent_port

            agent_base_url_local = f"http://{agent_host}:{agent_port}"
            agent_socket_url_local = f"ws://{agent_host}:{agent_port}"

            self.rest_client = RestClient(base_url=agent_base_url_local)
            self.socket_client = SocketClient(base_socket_url=agent_socket_url_local)
        else:
            self.agent_host = None
            self.agent_port = None
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
            response_payload = None

            data_field = response.get("data")

            # Legacy detailed execution payload
            if isinstance(data_field, dict) and "result_data" in data_field:
                response_payload = data_field["result_data"].get("data")
            # Simplified payload: data is the structured output string
            elif isinstance(data_field, str):
                response_payload = data_field
            # Backward compatibility for very old responses
            elif "output_data" in response:
                response_payload = response.get("output_data")

            if response_payload is None:
                return None

            if isinstance(response_payload, str):
                try:
                    return self.serializer.deserialize_object_from_structured(response_payload)
                except Exception:
                    pass

            return self.serializer.deserialize_object(response_payload)

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

        socket_iterator = self.socket_client.run_stream(
            self.agent_id, self.entrypoint_tag, input_args=input_args, input_kwargs=input_kwargs
        )

        def _iterator():
            try:
                for chunk in socket_iterator:
                    yield chunk
            except Exception as e:
                raw_message = str(e)
                friendly_message, code, suggestion = self._classify_stream_error(raw_message)
                raise RunAgentExecutionError(
                    code=code,
                    message=friendly_message,
                    suggestion=suggestion,
                    details={"raw_error": raw_message} if raw_message else None,
                )

        return _iterator()

    def _run_stream(self, *input_args, **input_kwargs):
        """Legacy method - use run_stream instead"""
        return self.run_stream(*input_args, **input_kwargs)

    def _build_suggestion(self, code: str, message: str) -> str | None:
        message_lower = (message or "").lower()

        # Check for permission/access errors first (403, permission denied, etc.)
        if (code == "PERMISSION_ERROR" or code == "AUTHENTICATION_ERROR" or 
            "403" in message or "permission" in message_lower or 
            "access denied" in message_lower or "do not have permission" in message_lower):
            dashboard_hint = f"https://app.run-agent.ai/dashboard/agents/{self.agent_id}"
            return (
                "This agent doesn't belong to your account or your API key doesn't have permission to access it. "
                f"Verify the agent ID is correct and that you have access to it. "
                f"You can check your agents in the dashboard: {dashboard_hint}. "
                f"If this is someone else's agent, you'll need to use their API key or have them share access."
            )

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

    def _classify_stream_error(self, raw_message: str) -> tuple[str, str, str | None]:
        """Derive a friendly error message, error code, and suggestion for streaming failures."""
        message = raw_message or "Unknown streaming error"
        lower_msg = message.lower()

        # Connection issues
        connection_keywords = [
            "connection refused",
            "failed to connect",
            "cannot connect",
            "did not respond",
            "connection closed",
        ]
        if any(keyword in lower_msg for keyword in connection_keywords):
            friendly = "Unable to connect to the streaming endpoint."
            suggestion = self._connection_hint()
            return friendly, "CONNECTION_ERROR", suggestion

        # Authentication / permission issues
        if any(keyword in lower_msg for keyword in ["unauthorized", "invalid token", "401"]):
            friendly = "Authentication failed for the streaming request."
            suggestion = self._build_suggestion("AUTHENTICATION_ERROR", raw_message)
            return friendly, "AUTHENTICATION_ERROR", suggestion

        if any(keyword in lower_msg for keyword in ["permission", "forbidden", "403", "access denied"]):
            friendly = "You do not have permission to stream this agent."
            suggestion = self._build_suggestion("PERMISSION_ERROR", raw_message)
            return friendly, "PERMISSION_ERROR", suggestion

        # Not found errors
        if "not found" in lower_msg or "404" in lower_msg:
            friendly = "The agent or entrypoint tag was not found."
            suggestion = self._build_suggestion("NOT_FOUND", raw_message)
            if not suggestion:
                suggestion = (
                    f"Confirm the agent ID and entrypoint `{self.entrypoint_tag}` exist. "
                    f"Review the agent in the dashboard: {self.dashboard_url}."
                )
            return friendly, "NOT_FOUND", suggestion

        # Timeout
        if "timeout" in lower_msg or "timed out" in lower_msg:
            friendly = "The streaming connection timed out."
            suggestion = (
                "Ensure the agent is still running and producing output, or increase the timeout value."
            )
            return friendly, "TIMEOUT", suggestion

        # Server errors
        if any(keyword in lower_msg for keyword in ["500", "internal server error", "bad gateway", "502", "503"]):
            friendly = "The server returned an error while streaming."
            suggestion = (
                "Try the request again. If the issue persists, inspect the agent logs or redeploy the agent."
            )
            return friendly, "SERVER_ERROR", suggestion

        # Default fallback
        suggestion = self._build_suggestion("STREAM_ERROR", raw_message)
        return message, "STREAM_ERROR", suggestion

    def _connection_hint(self) -> str:
        if self.local:
            if self.agent_host and self.agent_port:
                return (
                    f"Ensure the local agent is running at ws://{self.agent_host}:{self.agent_port} "
                    f"and that entrypoint `{self.entrypoint_tag}` exposes streaming output. "
                    "Restart the agent with `runagent serve` if needed."
                )
            return "Ensure the local agent is running and reachable before streaming."

        return (
            "Check your internet connection and confirm the agent is deployed in RunAgent Cloud. "
            f"Review its status in the dashboard: {self.dashboard_url}."
        )

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