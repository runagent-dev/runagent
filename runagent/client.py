# runagent/client.py
"""
RunAgent client for deploying and managing AI agents.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
import json
import time
import websocket
import threading

from .api import ApiClient
from .config import get_config, get_api_key
from .utils import package_agent, validate_agent_directory, parse_agent_metadata
from .exceptions import RunAgentError, AuthenticationError, DeploymentError

logger = logging.getLogger(__name__)

class RunAgentClient:
    """Client for interacting with the RunAgent service."""
    
    def __init__(self, api_key=None, base_url=None):
        # Get API key and base URL from env, config, or arguments
        self.api_key = api_key or get_api_key()
        self.base_url = base_url or os.environ.get("RUNAGENT_API_URL") or get_config().get("base_url")
        
        if not self.api_key:
            raise AuthenticationError("API key is required. Set it via constructor, RUNAGENT_API_KEY environment variable, or config file.")
            
        # Initialize API client
        self.api = ApiClient(self.api_key, self.base_url)
    
    def deploy(self, agent_path: str, agent_type: str = "langgraph") -> Dict[str, Any]:
        """
        Deploy an agent from the given path.
        
        Args:
            agent_path: Path to the agent directory
            agent_type: Type of agent framework (e.g., "langgraph")
            
        Returns:
            Dict with deployment information
        """
        try:
            # Validate agent directory
            validate_agent_directory(agent_path)
            
            # Package agent
            zip_path = package_agent(agent_path)
            
            # Upload agent
            result = self.api.upload_file(
                "deploy",
                zip_path,
                file_param_name="agent_code",
                additional_data={"agent_type": agent_type}
            )
            
            # Clean up temporary zip file
            try:
                os.unlink(zip_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            raise DeploymentError(f"Failed to deploy agent: {e}")
    
    def get_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get the status of a deployed agent.
        
        Args:
            deployment_id: ID of the deployment
            
        Returns:
            Dict with deployment status
        """
        return self.api.get(f"agents/{deployment_id}/status")
    
    def list_deployments(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all deployments.
        
        Args:
            status: Optional filter by status (e.g., "running", "failed")
            
        Returns:
            List of deployment information
        """
        params = {}
        if status:
            params["status"] = status
            
        return self.api.get("deployments", params=params)
    
    def run_agent(self, deployment_id: str, input_data: Dict[str, Any], webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger an agent run.
        
        Args:
            deployment_id: ID of the deployment
            input_data: Input data for the agent
            webhook_url: Optional webhook URL for result notification
            
        Returns:
            Dict with execution information
        """
        payload = {
            "input": input_data,
        }
        
        if webhook_url:
            payload["webhook_url"] = webhook_url
            
        return self.api.post(f"agents/{deployment_id}/run", json=payload)
    
    def get_execution_status(self, deployment_id: str, execution_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific execution.
        
        Args:
            deployment_id: ID of the deployment
            execution_id: ID of the execution
            
        Returns:
            Dict with execution status
        """
        return self.api.get(f"agents/{deployment_id}/executions/{execution_id}/status")
    
    def stream_logs(self, deployment_id: str, execution_id: Optional[str] = None, callback=None):
        """
        Stream logs from a deployment or execution.
        
        Args:
            deployment_id: ID of the deployment
            execution_id: Optional ID of a specific execution
            callback: Function to call with each log message
            
        Returns:
            WebSocket connection object with .close() method
        """
        # Determine WebSocket URL
        if execution_id:
            ws_url = f"ws://{self.base_url.replace('http://', '').replace('https://', '')}/execution-logs/{deployment_id}/{execution_id}"
        else:
            ws_url = f"ws://{self.base_url.replace('http://', '').replace('https://', '')}/logs/{deployment_id}"
        
        # Set up WebSocket connection
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=lambda ws, msg: callback(json.loads(msg)) if callback else print(msg),
            on_error=lambda ws, err: logger.error(f"WebSocket error: {err}"),
            on_close=lambda ws, close_status_code, close_msg: logger.debug("WebSocket connection closed")
        )
        
        # Start WebSocket in a thread
        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
        
        return ws
    
    def delete_agent(self, deployment_id: str) -> Dict[str, Any]:
        """
        Delete a deployed agent.
        
        Args:
            deployment_id: ID of the deployment
            
        Returns:
            Dict with deletion status
        """
        return self.api.delete(f"agents/{deployment_id}")
    
    def run_sandbox(self, agent_path: str, input_data: Dict[str, Any], agent_type: str = "langgraph") -> Dict[str, Any]:
        """
        Run an agent in sandbox mode.
        
        Args:
            agent_path: Path to the agent directory
            input_data: Input data for the agent
            agent_type: Type of agent framework
            
        Returns:
            Dict with sandbox execution results
        """
        try:
            # Validate agent directory
            validate_agent_directory(agent_path)
            
            # Package agent
            zip_path = package_agent(agent_path)
            
            # Upload agent to sandbox
            files = {"agent_code": open(zip_path, "rb")}
            data = {
                "agent_type": agent_type,
                "input": json.dumps(input_data)
            }
            
            result = self.api.upload_file(
                "sandbox/run",
                zip_path,
                file_param_name="agent_code",
                additional_data=data
            )
            
            # Clean up temporary zip file
            try:
                os.unlink(zip_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            raise RunAgentError(f"Failed to run agent in sandbox: {e}")