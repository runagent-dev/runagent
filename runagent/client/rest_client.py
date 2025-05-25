# runagent/client/rest_client.py
import os
import json
import zipfile
import tempfile
import requests
import time
from typing import Dict, Any, Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

class RestClient:
    """Client for remote server deployment via REST API"""
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize REST client for middleware server
        
        Args:
            api_url: URL of the middleware server
            api_key: API key for authentication
        """
        from runagent.utils.config import Config
        
        self.api_url = api_url or Config.get_base_url()
        self.api_key = api_key or Config.get_api_key()
        
        # Remove trailing slash
        if self.api_url.endswith('/'):
            self.api_url = self.api_url[:-1]
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'RunAgent-CLI/1.0'
            })
    
    def upload_agent(self, folder_path: str, metadata: Dict = None) -> Dict:
        """
        Upload agent folder to middleware server
        
        Args:
            folder_path: Path to folder containing agent files
            metadata: Additional metadata for upload
            
        Returns:
            Upload result with agent_id
        """
        try:
            folder_path = Path(folder_path)
            
            if not folder_path.exists():
                return {
                    'success': False,
                    'error': f'Folder not found: {folder_path}'
                }
            
            console.print(f"📤 Uploading agent from: [blue]{folder_path}[/blue]")
            
            # Create zip file
            with console.status("[bold green]🔧 Preparing files for upload...[/bold green]", spinner="dots"):
                zip_path = self._create_zip_from_folder(folder_path)
            
            console.print(f"📦 Created upload package: [cyan]{Path(zip_path).name}[/cyan]")
            
            # Prepare upload metadata
            upload_metadata = {
                'framework': metadata.get('framework', 'unknown') if metadata else 'unknown',
                'uploaded_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source_folder': str(folder_path),
                **(metadata or {})
            }
            
            # Upload to server
            console.print(f"🌐 Uploading to: [bold blue]{self.api_url}[/bold blue]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold green]Uploading...[/bold green]"),
                BarColumn(bar_width=40),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                upload_task = progress.add_task("Uploading...", total=100)
                
                # Simulate progress while uploading
                result = self._upload_to_server(zip_path, upload_metadata, progress, upload_task)
            
            # Clean up zip file
            os.unlink(zip_path)
            
            if result.get('success'):
                agent_id = result.get('agent_id')
                
                # Save deployment info locally
                self._save_deployment_info(agent_id, {
                    **upload_metadata,
                    'agent_id': agent_id,
                    'remote': True,
                    'api_url': self.api_url
                })
                
                console.print(Panel(
                    f"✅ [bold green]Upload successful![/bold green]\n"
                    f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                    f"🌐 Server: [blue]{self.api_url}[/blue]",
                    title="📤 Upload Complete",
                    border_style="green"
                ))
                
                return {
                    'success': True,
                    'agent_id': agent_id,
                    'api_url': self.api_url,
                    'message': f'Agent uploaded. Use "runagent start --id {agent_id}" to deploy, or "runagent deploy --id {agent_id}" for direct deployment.'
                }
            else:
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Upload failed: {str(e)}"
            }
    
    def _create_zip_from_folder(self, folder_path: Path) -> str:
        """Create a zip file from the agent folder"""
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, f"agent_{int(time.time())}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in folder_path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    # Add file to zip with relative path
                    arcname = file_path.relative_to(folder_path)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def _upload_to_server(self, zip_path: str, metadata: Dict, progress: Progress, task_id) -> Dict:
        """Upload zip file to middleware server"""
        try:
            upload_url = f"{self.api_url}/api/v1/agents/upload"
            
            # Prepare files and data
            with open(zip_path, 'rb') as f:
                files = {'file': (os.path.basename(zip_path), f, 'application/zip')}
                data = {
                    'metadata': json.dumps(metadata)
                }
                
                # Update progress during upload
                for i in range(0, 100, 10):
                    progress.update(task_id, completed=i)
                    time.sleep(0.1)
                
                response = self.session.post(
                    upload_url,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout
                )
                
                progress.update(task_id, completed=100)
            
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', f'HTTP {response.status_code}')
                except:
                    error_message = f'HTTP {response.status_code}: {response.text}'
                
                return {
                    'success': False,
                    'error': f"Server error: {error_message}"
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': f"Cannot connect to server at {self.api_url}. Please check the URL and your internet connection."
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "Upload timed out. Please try again or check your connection."
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Upload error: {str(e)}"
            }
    
    def start_agent(self, agent_id: str, config: Dict = None) -> Dict:
        """
        Start/deploy an uploaded agent on the middleware server
        
        Args:
            agent_id: ID of the uploaded agent
            config: Optional deployment configuration
            
        Returns:
            Deployment result
        """
        try:
            console.print(f"🚀 Starting agent: [bold magenta]{agent_id}[/bold magenta]")
            
            start_url = f"{self.api_url}/api/v1/agents/{agent_id}/start"
            
            payload = {
                'config': config or {},
                'started_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            response = self.session.post(start_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    endpoint = result.get('endpoint')
                    
                    console.print(Panel(
                        f"✅ [bold green]Agent started successfully![/bold green]\n"
                        f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                        f"🌐 Endpoint: [link]{endpoint}[/link]",
                        title="🚀 Deployment Complete",
                        border_style="green"
                    ))
                    
                    # Update local deployment info
                    self._update_deployment_info(agent_id, {
                        'status': 'running',
                        'endpoint': endpoint,
                        'started_at': payload['started_at']
                    })
                    
                    return {
                        'success': True,
                        'agent_id': agent_id,
                        'endpoint': endpoint,
                        'status': 'running'
                    }
                else:
                    return result
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', f'HTTP {response.status_code}')
                except:
                    error_message = f'HTTP {response.status_code}: {response.text}'
                
                return {
                    'success': False,
                    'error': f"Failed to start agent: {error_message}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Start agent failed: {str(e)}"
            }
    
    def deploy_agent(self, folder_path: str, metadata: Dict = None) -> Dict:
        """
        Upload and start agent in one operation
        
        Args:
            folder_path: Path to folder containing agent files
            metadata: Additional metadata
            
        Returns:
            Complete deployment result
        """
        console.print("🎯 [bold cyan]Starting full deployment (upload + start)...[/bold cyan]")
        
        # First upload
        upload_result = self.upload_agent(folder_path, metadata)
        
        if not upload_result.get('success'):
            return upload_result
        
        agent_id = upload_result.get('agent_id')
        
        # Then start
        start_result = self.start_agent(agent_id)
        
        if start_result.get('success'):
            return {
                'success': True,
                'agent_id': agent_id,
                'endpoint': start_result.get('endpoint'),
                'status': 'running',
                'message': f'Agent fully deployed and running. Endpoint: {start_result.get("endpoint")}'
            }
        else:
            return {
                'success': False,
                'error': f"Upload succeeded but start failed: {start_result.get('error')}",
                'agent_id': agent_id
            }
    
    def _save_deployment_info(self, agent_id: str, metadata: Dict):
        """Save deployment info for CLI reference"""
        deployments_dir = Path.cwd() / ".deployments"
        deployments_dir.mkdir(exist_ok=True)
        
        info_file = deployments_dir / f"{agent_id}.json"
        with open(info_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _update_deployment_info(self, agent_id: str, updates: Dict):
        """Update existing deployment info"""
        deployments_dir = Path.cwd() / ".deployments"
        info_file = deployments_dir / f"{agent_id}.json"
        
        if info_file.exists():
            try:
                with open(info_file, 'r') as f:
                    metadata = json.load(f)
                metadata.update(updates)
                with open(info_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except:
                pass  # Ignore errors updating deployment info
    
    def get_agent_status(self, agent_id: str) -> Dict:
        """Get status of a remote agent"""
        try:
            status_url = f"{self.api_url}/api/v1/agents/{agent_id}/status"
            response = self.session.get(status_url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f"Failed to get status: HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Status check failed: {str(e)}"
            }