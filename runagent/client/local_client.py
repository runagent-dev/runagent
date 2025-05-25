# runagent/client/local_client.py
import os
import json
import shutil
import importlib.util
import uuid
import time
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import subprocess
from rich.console import Console
from rich.panel import Panel

console = Console()

class LocalClient:
    """Client for local deployment and testing"""
    
    def __init__(self, deploy_dir: str = "deployments"):
        """
        Initialize local client
        
        Args:
            deploy_dir: Directory for local deployments
        """
        self.deploy_dir = Path(deploy_dir)
        self.deploy_dir.mkdir(exist_ok=True)
        
        # Local server info
        self.local_server_host = "127.0.0.1"
        self.local_server_port = 8450
    
    def deploy_agent(self, folder_path: str, metadata: Dict = None) -> Dict:
        """
        Deploy agent locally for testing
        
        Args:
            folder_path: Path to folder containing agent files
            metadata: Additional metadata for deployment
            
        Returns:
            Deployment result with agent_id
        """
        try:
            folder_path = Path(folder_path)
            
            if not folder_path.exists():
                return {
                    'success': False,
                    'error': f'Folder not found: {folder_path}'
                }
            
            # Generate agent ID
            agent_id = str(uuid.uuid4())[:8]
            agent_dir = self.deploy_dir / agent_id
            
            console.print(f"📦 Deploying agent locally with ID: [bold cyan]{agent_id}[/bold cyan]")
            
            # Create agent directory
            agent_dir.mkdir(exist_ok=True)
            
            # Copy all files from source folder
            self._copy_agent_files(folder_path, agent_dir)
            
            # Install requirements if they exist
            req_file = agent_dir / 'requirements.txt'
            if req_file.exists():
                console.print("📋 Installing dependencies...")
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", 
                        "-r", str(req_file), "--quiet"
                    ])
                    console.print("✅ Dependencies installed successfully")
                except subprocess.CalledProcessError as e:
                    console.print(f"⚠️ Warning: Failed to install some dependencies: {e}")
            
            # Create metadata file
            deployment_metadata = {
                'agent_id': agent_id,
                'deployed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'local': True,
                'folder_path': str(folder_path),
                'framework': metadata.get('framework', 'unknown') if metadata else 'unknown',
                **(metadata or {})
            }
            
            with open(agent_dir / 'metadata.json', 'w') as f:
                json.dump(deployment_metadata, f, indent=2)
            
            # Validate the agent
            validation_result = self._validate_agent(agent_dir)
            if not validation_result['valid']:
                # Clean up on validation failure
                shutil.rmtree(agent_dir)
                return {
                    'success': False,
                    'error': f"Agent validation failed: {validation_result['error']}"
                }
            
            # Save deployment info for CLI reference
            self._save_deployment_info(agent_id, deployment_metadata)
            
            console.print(Panel(
                f"✅ [bold green]Local deployment successful![/bold green]\n"
                f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                f"📁 Deployed to: [blue]{agent_dir}[/blue]\n"
                f"🌐 Endpoint: [link]http://{self.local_server_host}:{self.local_server_port}/agents/{agent_id}/run[/link]",
                title="🚀 Deployment Complete",
                border_style="green"
            ))
            
            return {
                'success': True,
                'agent_id': agent_id,
                'endpoint': f"http://{self.local_server_host}:{self.local_server_port}/agents/{agent_id}/run",
                'local': True,
                'deployment_path': str(agent_dir),
                'message': f'Agent deployed locally. Use "runagent serve" to start the local server, then "runagent run --id {agent_id} --local" to test.'
            }
            
        except Exception as e:
            # Clean up if deployment failed
            if 'agent_dir' in locals() and agent_dir.exists():
                shutil.rmtree(agent_dir)
                
            return {
                'success': False,
                'error': f"Local deployment failed: {str(e)}"
            }
    
    def _copy_agent_files(self, source_dir: Path, target_dir: Path):
        """Copy agent files from source to target directory"""
        essential_files = ['main.py', 'agent.py', 'requirements.txt', '.env']
        copied_files = []
        
        # Copy essential files first
        for file_name in essential_files:
            source_file = source_dir / file_name
            if source_file.exists():
                shutil.copy2(source_file, target_dir / file_name)
                copied_files.append(file_name)
        
        # Copy any additional Python files and configs
        for item in source_dir.iterdir():
            if item.name not in copied_files:
                if item.is_file() and (
                    item.suffix in ['.py', '.json', '.yaml', '.yml', '.txt', '.md'] or
                    item.name.startswith('.env')
                ):
                    shutil.copy2(item, target_dir / item.name)
                    copied_files.append(item.name)
                elif item.is_dir() and not item.name.startswith('.'):
                    # Copy subdirectories recursively
                    shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
                    copied_files.append(f"{item.name}/")
        
        console.print(f"📁 Copied files: {', '.join(copied_files)}")
    
    def _validate_agent(self, agent_dir: Path) -> Dict[str, Any]:
        """Validate that the agent has required files and structure"""
        required_files = ['main.py']
        
        # Check for required files
        missing_files = []
        for file_name in required_files:
            if not (agent_dir / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            return {
                'valid': False,
                'error': f"Missing required files: {missing_files}"
            }
        
        # Try to import and validate main.py
        main_file = agent_dir / 'main.py'
        try:
            # Add agent directory to path temporarily
            sys.path.insert(0, str(agent_dir))
            
            spec = importlib.util.spec_from_file_location("main", main_file)
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            
            # Check if run function exists
            if not hasattr(main_module, 'run') or not callable(main_module.run):
                return {
                    'valid': False,
                    'error': "main.py must contain a callable 'run' function"
                }
            
            return {'valid': True}
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Failed to validate main.py: {str(e)}"
            }
        finally:
            # Clean up path
            if str(agent_dir) in sys.path:
                sys.path.remove(str(agent_dir))
    
    def _save_deployment_info(self, agent_id: str, metadata: Dict):
        """Save deployment info for CLI reference"""
        deployments_dir = Path.cwd() / ".deployments"
        deployments_dir.mkdir(exist_ok=True)
        
        info_file = deployments_dir / f"{agent_id}.json"
        with open(info_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def run_agent(self, agent_id: str, input_data: Dict) -> Dict:
        """
        Run agent locally (used by local server)
        
        Args:
            agent_id: ID of the agent to run
            input_data: Input data for the agent
            
        Returns:
            Agent execution result
        """
        agent_dir = self.deploy_dir / agent_id
        
        if not agent_dir.exists():
            return {
                'success': False,
                'error': f'Agent {agent_id} not found in local deployments'
            }
        
        try:
            # Add agent directory to Python path
            sys.path.insert(0, str(agent_dir))
            
            # Import main module
            main_file = agent_dir / "main.py"
            spec = importlib.util.spec_from_file_location("main", main_file)
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            
            # Run agent
            result = main_module.run(input_data)
            return result
        
        except Exception as e:
            return {
                'success': False,
                'error': f"Agent execution failed: {str(e)}"
            }
        
        finally:
            # Clean up Python path
            if str(agent_dir) in sys.path:
                sys.path.remove(str(agent_dir))
    
    def list_local_agents(self) -> Dict:
        """List all locally deployed agents"""
        agents = []
        
        if not self.deploy_dir.exists():
            return {'success': True, 'agents': agents}
        
        for agent_dir in self.deploy_dir.iterdir():
            if agent_dir.is_dir():
                metadata_file = agent_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        agents.append(metadata)
                    except:
                        # Skip invalid metadata files
                        continue
        
        return {'success': True, 'agents': agents}
    
    def get_agent_info(self, agent_id: str) -> Dict:
        """Get information about a local agent"""
        agent_dir = self.deploy_dir / agent_id
        
        if not agent_dir.exists():
            return {
                'success': False,
                'error': f'Agent {agent_id} not found'
            }
        
        metadata_file = agent_dir / 'metadata.json'
        if not metadata_file.exists():
            return {
                'success': False,
                'error': f'Metadata not found for agent {agent_id}'
            }
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            return {
                'success': True,
                'agent_info': metadata
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to read agent metadata: {str(e)}'
            }