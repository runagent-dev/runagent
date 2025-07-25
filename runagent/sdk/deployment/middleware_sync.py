# runagent/sdk/deployment/middleware_sync.py
# NEW FILE - Create this file

import time
from datetime import datetime
from typing import Optional, Dict, Any
from rich.console import Console

console = Console()


class MiddlewareSync:
    """Handle synchronization with middleware server"""
    
    def __init__(self, rest_client=None):
        self.rest_client = rest_client
        self.enabled = False
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to middleware and set enabled status"""
        try:
            if not self.rest_client:
                from runagent.sdk.rest_client import RestClient
                from runagent.utils.config import Config
                
                api_key = Config.get_api_key()
                if not api_key:
                    console.print("ℹ️ [dim]No API key configured - middleware sync disabled[/dim]")
                    return
                
                self.rest_client = RestClient()
            
            # Test health endpoint
            response = self.rest_client.http.get("health", timeout=3)
            if response.status_code == 200:
                self.enabled = True
                console.print("✅ [green]Middleware connection verified[/green]")
            else:
                console.print(f"⚠️ [yellow]Middleware health check failed: {response.status_code}[/yellow]")
                
        except Exception as e:
            console.print(f"ℹ️ [dim]Middleware sync disabled: {e}[/dim]")
            self.enabled = False
    
    def sync_agent(self, agent_id: str, agent_config, host: str, port: int, agent_path: str) -> bool:
        """Sync agent information to middleware"""
        if not self.enabled:
            return False
            
        try:
            console.print(f"🔄 [cyan]Syncing agent to middleware: {agent_id}[/cyan]")
            
            # Prepare agent data
            agent_data = {
                "local_agent_id": agent_id,
                "name": agent_config.agent_name,
                "framework": agent_config.framework,
                "version": agent_config.version,
                "path": str(agent_path),
                "host": host,
                "port": port,
                "entrypoints": [ep.dict() for ep in agent_config.agent_architecture.entrypoints],
                "status": "running",
                "sync_timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to middleware
            response = self.rest_client.http.post(
                "local-agents", 
                data=agent_data, 
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                action = result.get('action', 'synced')
                console.print(f"✅ [green]Agent {action} in middleware: {agent_id}[/green]")
                return True
            else:
                console.print(f"⚠️ [yellow]Agent sync failed: {response.status_code} - {response.text}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"⚠️ [yellow]Agent sync error: {e}[/yellow]")
            return False
    
    def start_invocation(self, agent_id: str, local_invocation_id: str, 
                        input_data: Dict[str, Any], entrypoint_tag: str,
                        client_info: Dict[str, Any]) -> Optional[str]:
        """Start invocation tracking in middleware"""
        if not self.enabled:
            return None
            
        try:
            invocation_data = {
                "local_agent_id": agent_id,
                "input_data": input_data,
                "entrypoint_tag": entrypoint_tag,
                "source": "local",
                "sdk_type": "local_server",
                "client_info": {
                    **client_info,
                    "local_invocation_id": local_invocation_id,
                },
                "local_timestamp": time.time()
            }
            
            response = self.rest_client.http.post(
                "local-invocations", 
                data=invocation_data, 
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                middleware_id = result.get("invocation_id")
                console.print(f"✅ [green]Middleware invocation started: {middleware_id[:8] if middleware_id else 'none'}...[/green]")
                return middleware_id
            else:
                console.print(f"⚠️ [yellow]Middleware invocation start failed: {response.status_code}[/yellow]")
                return None
                
        except Exception as e:
            console.print(f"⚠️ [yellow]Middleware invocation start error: {e}[/yellow]")
            return None
    
    def complete_invocation(self, middleware_invocation_id: str, 
                          output_data: Optional[Dict[str, Any]] = None,
                          execution_time_ms: Optional[float] = None,
                          error_detail: Optional[str] = None) -> bool:
        """Complete invocation tracking in middleware"""
        if not self.enabled or not middleware_invocation_id:
            return False
            
        try:
            update_data = {
                "completed_timestamp": time.time()
            }
            
            if execution_time_ms is not None:
                update_data["execution_time_ms"] = execution_time_ms
                
            if error_detail:
                update_data["error_detail"] = error_detail
            elif output_data is not None:
                update_data["output_data"] = output_data
            
            response = self.rest_client.http.put(
                f"local-invocations/{middleware_invocation_id}", 
                data=update_data, 
                timeout=5
            )
            
            if response.status_code == 200:
                console.print(f"✅ [green]Middleware invocation completed: {middleware_invocation_id[:8]}...[/green]")
                return True
            else:
                console.print(f"⚠️ [yellow]Middleware invocation completion failed: {response.status_code}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"⚠️ [yellow]Middleware invocation completion error: {e}[/yellow]")
            return False

    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from middleware when server shuts down"""
        if not self.enabled:
            return False
            
        try:
            response = self.rest_client.http.delete(
                f"local-agents/{agent_id}", 
                timeout=5
            )
            
            if response.status_code == 200:
                console.print(f"✅ [green]Agent removed from middleware: {agent_id}[/green]")
                return True
            else:
                console.print(f"⚠️ [yellow]Agent removal failed: {response.status_code}[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"⚠️ [yellow]Agent removal error: {e}[/yellow]")
            return False


def get_middleware_sync() -> MiddlewareSync:
    """Get a configured middleware sync instance"""
    return MiddlewareSync()