"""
Local deployment management.
"""

import typing as t
import requests
import time
from pathlib import Path

from ..local_client import LocalClient
from ..exceptions import ValidationError, ConnectionError


class LocalDeployment:
    """Manage local agent deployments"""
    
    def __init__(self, config):
        """
        Initialize local deployment manager.
        
        Args:
            config: SDK configuration object
        """
        self.config = config
        self.client = LocalClient()
        self.local_server_url = "http://127.0.0.1:8450"
    
    def deploy_agent(
        self,
        folder_path: str,
        framework: t.Optional[str] = None,
        replace_agent_id: t.Optional[str] = None
    ) -> t.Dict[str, t.Any]:
        """
        Deploy an agent locally.
        
        Args:
            folder_path: Path to agent folder
            framework: Framework type (auto-detected if None)
            replace_agent_id: Optional agent to replace
            
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
        
        return self.client.deploy_agent(
            folder_path=str(folder_path),
            metadata=metadata,
            replace_agent_id=replace_agent_id
        )
    
    def list_agents(self) -> t.List[t.Dict[str, t.Any]]:
        """List all local agents"""
        result = self.client.list_local_agents()
        return result.get("agents", []) if result.get("success") else []
    
    def get_agent_info(self, agent_id: str) -> t.Dict[str, t.Any]:
        """Get information about a local agent"""
        return self.client.get_agent_info(agent_id)
    
    def run_agent(self, agent_id: str, input_data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """
        Run a local agent via HTTP server (not direct execution)
        
        This method attempts to run the agent via the local HTTP server first.
        If the server is not running, it falls back to direct execution.
        """
        # First, try to run via HTTP server
        try:
            result = self._run_agent_via_http(agent_id, input_data)
            
            # Fix the response format - the server returns a different format than expected
            if isinstance(result, dict):
                # Check if this is the server response format
                if 'success' in result and 'result' in result and 'agent_id' in result:
                    # This is the server format, return as-is but ensure it matches expected format
                    return result
                elif 'result' in result and 'errors' in result:
                    # This is the direct execution format, convert to server format
                    return {
                        'success': result.get('success', True),
                        'result': result.get('result'),
                        'error': result.get('errors')[0] if result.get('errors') else None,
                        'agent_id': agent_id
                    }
            
            return result
            
        except ConnectionError:
            # If HTTP server is not available, fall back to direct execution
            print("⚠️ Local server not running, executing agent directly...")
            return self.client.run_agent(agent_id, input_data)
    
    def _run_agent_via_http(self, agent_id: str, input_data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """
        Run agent via HTTP server
        
        Args:
            agent_id: Agent identifier
            input_data: Input data for the agent
            
        Returns:
            Agent execution result
            
        Raises:
            ConnectionError: If server is not reachable
        """
        url = f"{self.local_server_url}/agents/{agent_id}/run"
        
        try:
            # Make HTTP request to local server
            response = requests.post(
                url,
                json=input_data,
                timeout=300,  # 5 minute timeout
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Debug: Print the raw response to understand the format
                print(f"🔍 Raw HTTP response: {result}")
                
                # The server response format is different from what we expect
                # Server returns: {"success": bool, "result": {...}, "error": str|null, "execution_time": float, "agent_id": str}
                # We need to check if the result is successful and extract the content properly
                
                if result.get('success') and result.get('result'):
                    # Server returned success - return the result in the expected format
                    return {
                        'success': True,
                        'result': result['result'],
                        'error': None,
                        'agent_id': agent_id,
                        'execution_time': result.get('execution_time')
                    }
                else:
                    # Server returned failure - check for error details
                    error_msg = result.get('error') or 'Unknown server error'
                    return {
                        'success': False,
                        'result': None,
                        'error': error_msg,
                        'agent_id': agent_id,
                        'execution_time': result.get('execution_time')
                    }
            else:
                # Try to get error details
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', f'HTTP {response.status_code}')
                except:
                    error_msg = f'HTTP {response.status_code}: {response.text}'
                
                return {
                    'success': False,
                    'result': None,
                    'error': f"Server error: {error_msg}",
                    'status_code': response.status_code,
                    'agent_id': agent_id
                }
        
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to local server at {self.local_server_url}. "
                "Make sure the server is running with 'runagent serve'"
            )
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'result': None,
                'error': "Request timed out. Agent execution took too long.",
                'agent_id': agent_id
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': f"HTTP request failed: {str(e)}",
                'agent_id': agent_id
            }
    
    def check_server_status(self) -> t.Dict[str, t.Any]:
        """
        Check if local server is running and get its status
        
        Returns:
            Server status information
        """
        try:
            response = requests.get(f"{self.local_server_url}/health", timeout=5)
            if response.status_code == 200:
                return {
                    'running': True,
                    'url': self.local_server_url,
                    'status': response.json()
                }
            else:
                return {
                    'running': False,
                    'error': f'Server returned HTTP {response.status_code}'
                }
        except requests.exceptions.ConnectionError:
            return {
                'running': False,
                'error': 'Server not reachable'
            }
        except Exception as e:
            return {
                'running': False,
                'error': str(e)
            }
    
    def run_agent_direct(self, agent_id: str, input_data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
        """
        Run agent directly (bypass HTTP server) - for SDK use
        
        This method runs the agent directly in the same process,
        not through the HTTP server.
        """
        return self.client.run_agent(agent_id, input_data)
    
    def delete_agent(self, agent_id: str) -> t.Dict[str, t.Any]:
        """Delete a local agent"""
        return self.client.delete_agent(agent_id)
    
    def get_capacity_info(self) -> t.Dict[str, t.Any]:
        """Get local database capacity information"""
        return self.client.get_capacity_info()
    
    def cleanup_old_records(self, days_old: int = 30) -> t.Dict[str, t.Any]:
        """Clean up old database records"""
        return self.client.cleanup_old_runs(days_old)
    
    def get_database_stats(self) -> t.Dict[str, t.Any]:
        """Get database statistics"""
        return self.client.get_database_stats()
    
    def start_server(self, port: int = 8450, host: str = "127.0.0.1", debug: bool = False):
        """Start local FastAPI server"""
        from ...server.local_server import LocalServer
        server = LocalServer(port=port, host=host)
        server.start(debug=debug)
    
    def _detect_framework(self, folder_path: Path) -> str:
        """Auto-detect framework from project files"""
        framework_keywords = {
            'langgraph': ['langgraph', 'StateGraph', 'Graph'],
            'langchain': ['langchain', 'ConversationChain', 'AgentExecutor'],
            'llamaindex': ['llama_index', 'VectorStoreIndex', 'QueryEngine']
        }
        
        for file_to_check in ['main.py', 'agent.py']:
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
        req_file = folder_path / 'requirements.txt'
        if req_file.exists():
            try:
                content = req_file.read_text().lower()
                for framework, keywords in framework_keywords.items():
                    if any(keyword.lower() in content for keyword in keywords):
                        return framework
            except:
                pass
        
        return 'unknown'