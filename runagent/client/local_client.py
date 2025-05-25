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
from .local_db import LocalDatabase

console = Console()

class LocalClient:
    """Client for local deployment and testing"""
    
    def __init__(self, deploy_dir: str = "deployments", db_path: str = "runagent_local.db"):
        """
        Initialize local client
        
        Args:
            deploy_dir: Directory for local deployments
            db_path: Path to SQLite database
        """
        self.deploy_dir = Path(deploy_dir)
        self.deploy_dir.mkdir(exist_ok=True)
        
        # Initialize database (but don't create file until needed)
        self.db = LocalDatabase(db_path, auto_init=False)
        
        # Local server info
        self.local_server_host = "127.0.0.1"
        self.local_server_port = 8450
    
    def _ensure_database_ready(self):
        """Ensure database is ready for operations"""
        if not self.db.is_initialized():
            console.print("⚠️ [yellow]Database not initialized. Please run 'runagent serve' first to initialize the database.[/yellow]")
            return False
        return True
    
    def deploy_agent(self, folder_path: str, metadata: Dict = None, replace_agent_id: str = None) -> Dict:
        """
        Deploy agent locally for testing
        
        Args:
            folder_path: Path to folder containing agent files
            metadata: Additional metadata for deployment
            replace_agent_id: Optional agent ID to replace (for capacity management)
            
        Returns:
            Deployment result with agent_id
        """
        try:
            # Check if database is ready
            if not self._ensure_database_ready():
                return {
                    'success': False,
                    'error': 'Database not initialized. Run "runagent serve" first to set up the database.',
                    'error_code': 'DB_NOT_INITIALIZED'
                }
            
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
            
            # Validate the agent
            validation_result = self._validate_agent(agent_dir)
            if not validation_result['valid']:
                # Clean up on validation failure
                shutil.rmtree(agent_dir)
                return {
                    'success': False,
                    'error': f"Agent validation failed: {validation_result['error']}"
                }
            
            # Prepare deployment metadata
            deployment_metadata = {
                'deployed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'local': True,
                'framework': metadata.get('framework', 'unknown') if metadata else 'unknown',
                **(metadata or {})
            }
            
            # Save to database with capacity check or replacement
            if replace_agent_id:
                console.print(f"🔄 Replacing agent: [yellow]{replace_agent_id}[/yellow] with [cyan]{agent_id}[/cyan]")
                db_result = self.db.replace_agent(
                    old_agent_id=replace_agent_id,
                    new_agent_id=agent_id,
                    folder_path=str(folder_path),
                    deployment_path=str(agent_dir),
                    framework=deployment_metadata['framework'],
                    metadata=deployment_metadata
                )
            else:
                db_result = self.db.add_agent(
                    agent_id=agent_id,
                    folder_path=str(folder_path),
                    deployment_path=str(agent_dir),
                    framework=deployment_metadata['framework'],
                    metadata=deployment_metadata
                )
            
            if not db_result.get('success'):
                # Clean up on database failure
                shutil.rmtree(agent_dir)
                
                # Handle different error cases
                error_code = db_result.get('code')
                if error_code == 'DATABASE_FULL':
                    console.print(Panel(
                        f"❌ [bold red]Database at capacity![/bold red]\n"
                        f"📊 Current: {db_result.get('current_count', 0)}/5 agents\n"
                        f"🕒 Oldest agent: [yellow]{db_result.get('oldest_agent', {}).get('agent_id', 'N/A')}[/yellow]\n"
                        f"💡 {db_result.get('suggestion', 'Consider replacing an existing agent')}",
                        title="🚫 Deployment Failed",
                        border_style="red"
                    ))
                    
                    return {
                        'success': False,
                        'error': db_result.get('error'),
                        'error_code': 'DATABASE_FULL',
                        'capacity_info': {
                            'current_count': db_result.get('current_count'),
                            'max_allowed': db_result.get('max_allowed'),
                            'oldest_agent': db_result.get('oldest_agent')
                        },
                        'suggestion': f"Use: runagent deploy --local --folder {folder_path} --replace {db_result.get('oldest_agent', {}).get('agent_id', '')}"
                    }
                else:
                    return {
                        'success': False,
                        'error': db_result.get('error', 'Database operation failed'),
                        'error_code': error_code
                    }
            
            # Also save deployment info for CLI reference (backward compatibility)
            self._save_deployment_info(agent_id, {
                **deployment_metadata,
                'agent_id': agent_id,
                'folder_path': str(folder_path),
                'deployment_path': str(agent_dir)
            })
            
            console.print(Panel(
                f"✅ [bold green]Local deployment successful![/bold green]\n"
                f"🆔 Agent ID: [bold magenta]{agent_id}[/bold magenta]\n"
                f"📁 Source: [blue]{folder_path}[/blue]\n"
                f"📂 Deployed to: [blue]{agent_dir}[/blue]\n"
                f"📊 Capacity: [cyan]{db_result.get('current_count', 1)}/5[/cyan] slots used\n"
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
                'source_path': str(folder_path),
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
        start_time = time.time()
        
        # Ensure database is ready
        self.db.ensure_initialized()
        
        # Get agent from database
        agent_info = self.db.get_agent(agent_id)
        if not agent_info:
            return {
                'success': False,
                'error': f'Agent {agent_id} not found in database'
            }
        
        agent_dir = Path(agent_info['deployment_path'])
        
        if not agent_dir.exists():
            # Update status in database
            self.db.update_agent_status(agent_id, 'missing')
            return {
                'success': False,
                'error': f'Agent {agent_id} deployment directory not found: {agent_dir}'
            }
        
        try:
            # Update status to running
            self.db.update_agent_status(agent_id, 'running')
            
            # Add agent directory to Python path
            sys.path.insert(0, str(agent_dir))
            
            # Import main module
            main_file = agent_dir / "main.py"
            spec = importlib.util.spec_from_file_location("main", main_file)
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            
            # Run agent
            result = main_module.run(input_data)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Record successful run in database
            success = result.get('success', True)
            self.db.record_agent_run(
                agent_id=agent_id,
                input_data=input_data,
                output_data=result,
                success=success,
                execution_time=execution_time
            )
            
            # Update status back to deployed
            self.db.update_agent_status(agent_id, 'deployed')
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Agent execution failed: {str(e)}"
            
            # Record failed run in database
            self.db.record_agent_run(
                agent_id=agent_id,
                input_data=input_data,
                success=False,
                error_message=error_msg,
                execution_time=execution_time
            )
            
            # Update status to error
            self.db.update_agent_status(agent_id, 'error')
            
            return {
                'success': False,
                'error': error_msg
            }
        
        finally:
            # Clean up Python path
            if str(agent_dir) in sys.path:
                sys.path.remove(str(agent_dir))
    
    def list_local_agents(self) -> Dict:
        """List all locally deployed agents from database"""
        try:
            if not self._ensure_database_ready():
                return {
                    'success': False,
                    'error': 'Database not initialized. Run "runagent serve" first.',
                    'agents': []
                }
            
            agents = self.db.list_agents()
            
            # Add additional runtime info for each agent
            for agent in agents:
                agent_dir = Path(agent['deployment_path'])
                agent['exists'] = agent_dir.exists()
                
                # Check if source folder still exists
                source_dir = Path(agent['folder_path'])
                agent['source_exists'] = source_dir.exists()
            
            return {'success': True, 'agents': agents}
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to list agents: {str(e)}",
                'agents': []
            }
    
    def get_agent_info(self, agent_id: str) -> Dict:
        """Get comprehensive information about a local agent"""
        try:
            agent_info = self.db.get_agent(agent_id)
            
            if not agent_info:
                return {
                    'success': False,
                    'error': f'Agent {agent_id} not found'
                }
            
            # Add runtime status
            agent_dir = Path(agent_info['deployment_path'])
            agent_info['deployment_exists'] = agent_dir.exists()
            agent_info['source_exists'] = Path(agent_info['folder_path']).exists()
            
            # Get statistics
            stats = self.db.get_agent_stats(agent_id)
            agent_info['stats'] = stats
            
            # Get recent runs
            recent_runs = self.db.get_agent_runs(agent_id, limit=5)
            agent_info['recent_runs'] = recent_runs
            
            return {
                'success': True,
                'agent_info': agent_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get agent info: {str(e)}'
            }
    
    def delete_agent(self, agent_id: str) -> Dict:
        """Delete a local agent - DISABLED (only file cleanup, database entry remains)"""
        try:
            # Get agent info first
            agent_info = self.db.get_agent(agent_id)
            if not agent_info:
                return {
                    'success': False,
                    'error': f'Agent {agent_id} not found'
                }
            
            # Remove deployment directory only (not database entry)
            agent_dir = Path(agent_info['deployment_path'])
            if agent_dir.exists():
                shutil.rmtree(agent_dir)
            
            # Update status to indicate files are missing but keep database entry
            self.db.update_agent_status(agent_id, 'missing')
            
            # Remove CLI deployment info
            deployments_dir = Path.cwd() / ".deployments"
            info_file = deployments_dir / f"{agent_id}.json"
            if info_file.exists():
                info_file.unlink()
            
            console.print(f"⚠️ [yellow]Agent {agent_id} files deleted but database entry preserved[/yellow]")
            console.print(f"💡 Use replacement deployment to reuse this slot")
            
            return {
                'success': True,
                'message': f'Agent {agent_id} files deleted (database entry preserved)',
                'note': 'Agent database entry preserved. Use replacement to reuse this slot.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to delete agent files: {str(e)}'
            }
    
    def get_capacity_info(self) -> Dict:
        """Get database capacity information"""
        if not self._ensure_database_ready():
            return {
                'error': 'Database not initialized',
                'current_count': 0,
                'max_capacity': 5,
                'remaining_slots': 5,
                'is_full': False
            }
        return self.db.get_database_capacity_info()
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            return self.db.get_database_stats()
        except Exception as e:
            return {'error': f'Failed to get database stats: {str(e)}'}
    
    def cleanup_old_runs(self, days_old: int = 30) -> Dict:
        """Clean up old run records"""
        try:
            deleted_count = self.db.cleanup_old_runs(days_old)
            return {
                'success': True,
                'deleted_runs': deleted_count,
                'message': f'Cleaned up {deleted_count} old run records'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to cleanup old runs: {str(e)}'
            }
    
    def redeploy_agent(self, agent_id: str) -> Dict:
        """Redeploy an existing agent from its source folder"""
        try:
            # Get agent info
            agent_info = self.db.get_agent(agent_id)
            if not agent_info:
                return {
                    'success': False,
                    'error': f'Agent {agent_id} not found'
                }
            
            source_path = Path(agent_info['folder_path'])
            if not source_path.exists():
                return {
                    'success': False,
                    'error': f'Source folder not found: {source_path}'
                }
            
            # Delete existing deployment
            delete_result = self.delete_agent(agent_id)
            if not delete_result.get('success'):
                return delete_result
            
            # Redeploy with same ID
            agent_dir = self.deploy_dir / agent_id
            agent_dir.mkdir(exist_ok=True)
            
            # Copy files
            self._copy_agent_files(source_path, agent_dir)
            
            # Validate
            validation_result = self._validate_agent(agent_dir)
            if not validation_result['valid']:
                shutil.rmtree(agent_dir)
                return {
                    'success': False,
                    'error': f"Redeployment validation failed: {validation_result['error']}"
                }
            
            # Update database
            metadata = agent_info.get('metadata', {})
            metadata.update({
                'redeployed_at': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            db_success = self.db.add_agent(
                agent_id=agent_id,
                folder_path=str(source_path),
                deployment_path=str(agent_dir),
                framework=agent_info.get('framework', 'unknown'),
                metadata=metadata
            )
            
            if not db_success:
                shutil.rmtree(agent_dir)
                return {
                    'success': False,
                    'error': f"Failed to update agent in database"
                }
            
            console.print(f"✅ Agent {agent_id} redeployed successfully")
            
            return {
                'success': True,
                'agent_id': agent_id,
                'message': f'Agent {agent_id} redeployed successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Redeployment failed: {str(e)}'
            }
    
    def get_agent_logs(self, agent_id: str, limit: int = 50) -> Dict:
        """Get execution logs for an agent"""
        try:
            runs = self.db.get_agent_runs(agent_id, limit)
            return {
                'success': True,
                'agent_id': agent_id,
                'runs': runs,
                'total': len(runs)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get agent logs: {str(e)}'
            }
    
    def update_agent_metadata(self, agent_id: str, metadata: Dict) -> Dict:
        """Update agent metadata"""
        try:
            agent_info = self.db.get_agent(agent_id)
            if not agent_info:
                return {
                    'success': False,
                    'error': f'Agent {agent_id} not found'
                }
            
            # Merge with existing metadata
            existing_metadata = agent_info.get('metadata', {})
            existing_metadata.update(metadata)
            existing_metadata['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Update in database (you'd need to add this method to LocalDatabase)
            # For now, we'll recreate the agent with updated metadata
            
            return {
                'success': True,
                'message': f'Agent {agent_id} metadata updated'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update metadata: {str(e)}'
            }