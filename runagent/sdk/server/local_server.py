import json
import os
import subprocess
import sys
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from runagent.sdk.server.socket_utils import AgentWebSocketHandler

import uvicorn
from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from rich.console import Console
from enum import Enum
from runagent.sdk.db import DBService
from runagent.sdk.server.framework import get_executor
from runagent.utils.agent import detect_framework, get_agent_config
from runagent.utils.schema import AgentInfo, AgentRunRequest, AgentRunResponse, WebSocketActionType, WebSocketAgentRequest
from runagent.utils.imports import PackageImporter
from runagent.utils.schema import MessageType
from runagent.sdk.server.socket_utils import AgentWebSocketHandler
from runagent.utils.port import PortManager
from runagent.utils.serializer import CoreSerializer
from runagent.utils.logs import DatabaseLogHandler
from runagent.sdk.deployment.middleware_sync import get_middleware_sync
from runagent.sdk.deployment.middleware_sync import MiddlewareSyncService
from runagent.sdk.config import SDKConfig

from runagent.utils.port import PortManager
from runagent.utils.agent import detect_framework, get_agent_config

console = Console()


class LocalServer:
    """FastAPI-based local server for testing deployed agents - ENHANCED with middleware sync"""

    def __init__(
        self,
        db_service: DBService,
        agent_id: str,
        agent_path: Path,
        port: int = 8450,
        host: str = "127.0.0.1",
    ):
        self.db_service = db_service
        self.port = port
        self.host = host
        self.agent_id = agent_id
        self.agent_path = agent_path
        self.importer = PackageImporter(verbose=True)
        self.serializer = CoreSerializer(max_size_mb=5.0)
        
        # Initialize middleware sync service
        try:
            self.config = SDKConfig()
            self.middleware_sync = MiddlewareSyncService(self.config)
        except Exception as e:
            console.print(f"[yellow]Could not initialize middleware sync: {e}[/yellow]")
            self.middleware_sync = None

        self.agent_config = get_agent_config(agent_path)
        self.agent_name = self.agent_config.agent_name
        self.agent_version = self.agent_config.version

        self.agent_framework = self.agent_config.framework.value
        self.agent_architecture = self.agent_config.agent_architecture  

        # Install dependencies if requirements.txt exists
        self._install_dependencies()

        # Set environment variables from agent config
        for key, value in self.agent_config.env_vars.items():
            os.environ[key] = str(value)

        self.agentic_executor = get_executor(
            self.agent_path, self.agent_framework, self.agent_architecture.entrypoints
        )

        # Handle agent setup and sync to middleware
        self._ensure_agent_in_database()
        
        self.websocket_handler = AgentWebSocketHandler(self.db_service, self.middleware_sync)
        self.start_time = time.time()
        self._setup_logging()

        self.app = self._setup_fastapi_app()
        self._setup_websocket_routes()
        self._setup_routes()
        self.agent_synced_to_middleware = False


    async def _sync_agent_to_middleware_and_wait(self):
        """Sync agent to middleware and wait for completion - FIXED VERSION"""
        if not hasattr(self, 'middleware_sync') or not self.middleware_sync:
            console.print("[dim]Middleware sync not available[/dim]")
            return False
            
        if not self.middleware_sync.sync_enabled:
            console.print("[dim]Middleware sync disabled (no API key configured)[/dim]")
            return False

        try:
            # Prepare agent data for sync
            agent_data = {
                "local_agent_id": self.agent_id,  
                "name": self.agent_name,
                "framework": self.agent_framework,
                "version": self.agent_version,
                "path": str(self.agent_path),
                "host": self.host,
                "port": self.port,
                "entrypoints": [ep.dict() for ep in self.agent_architecture.entrypoints],
                "status": "running",
                "sync_timestamp": datetime.utcnow().isoformat()
            }

            console.print(f"[cyan]Syncing agent {self.agent_id} to middleware...[/cyan]")
            console.print(f"[dim]Agent data: {agent_data['name']} ({agent_data['framework']})[/dim]")
            
            sync_result = await self.middleware_sync.sync_agent_startup(self.agent_id, agent_data)
            
            if sync_result:
                console.print(f"✅ [green]Agent successfully synced to middleware[/green]")
                self.agent_synced_to_middleware = True
                return True
            else:
                console.print(f"[yellow]Agent sync failed - logs will be local only[/yellow]")
                self.agent_synced_to_middleware = False
                return False

        except Exception as e:
            console.print(f"❌ [red]Failed to sync agent to middleware: {e}[/red]")
            self.agent_synced_to_middleware = False
            return False

    def create_endpoint_handler_with_tracking(self, runner, agent_id, entrypoint_tag):
        """ENHANCED - Create endpoint handler with invocation tracking and middleware sync"""

        async def run_agent(request: AgentRunRequest):
            """Run a deployed agent with full invocation tracking and middleware sync"""
            
            # Start local invocation tracking
            invocation_id = self.db_service.start_invocation(
                agent_id=agent_id,
                input_data={
                    "input_args": request.input_data.input_args,
                    "input_kwargs": request.input_data.input_kwargs
                },
                entrypoint_tag=entrypoint_tag,
                sdk_type="local_server",
                client_info={
                    "server_host": self.host,
                    "server_port": self.port,
                    "agent_name": self.agent_name,
                    "agent_framework": self.agent_framework
                }
            )

            self.log_execution_start(invocation_id, entrypoint_tag)

            middleware_invocation_id = None
            if (hasattr(self, 'middleware_sync') and 
                self.middleware_sync and 
                self.middleware_sync.is_sync_enabled()):
                
                try:
                    import asyncio
                    middleware_invocation_id = await self.middleware_sync.sync_invocation_start({
                        "agent_id": agent_id,
                        "input_data": {
                            "input_args": request.input_data.input_args,
                            "input_kwargs": request.input_data.input_kwargs
                        },
                        "entrypoint_tag": entrypoint_tag,
                        "sdk_type": "local_server",
                        "client_info": {
                            "server_host": self.host,
                            "server_port": self.port,
                            "agent_name": self.agent_name,
                            "agent_framework": self.agent_framework
                        }
                    })
                except Exception as e:
                    console.print(f"[yellow]Middleware sync start failed: {e}[/yellow]")

            start_time = time.time()
            execution_success = False
            error_detail = None
            result_data = None

            try:
                console.print(f"Running agent: [cyan]{agent_id}[/cyan] (invocation: {invocation_id}...)")

                result_data = await runner(
                    *request.input_data.input_args, **request.input_data.input_kwargs
                )

                result_str = self.serializer.serialize_object(result_data)
                execution_time = time.time() - start_time
                execution_success = True
                self.log_execution_complete(invocation_id, True, execution_time)

                # Complete local invocation tracking with success
                try:
                    serializable_output = self._convert_to_serializable(result_data)
                    
                    self.db_service.complete_invocation(
                        invocation_id=invocation_id,
                        output_data=serializable_output,
                        execution_time_ms=execution_time * 1000
                    )
                    console.print(f"✅ [green]Local invocation tracking completed successfully[/green]")
                    
                except Exception as e:
                    console.print(f"❌ [red]Failed to complete local invocation tracking: {str(e)}[/red]")
                    # Try with minimal safe data
                    try:
                        self.db_service.complete_invocation(
                            invocation_id=invocation_id,
                            output_data={
                                "execution_completed": True,
                                "result_type": str(type(result_data)),
                                "result_length": len(str(result_data)) if result_data else 0,
                                "serialization_note": f"Could not serialize result: {str(e)}"
                            },
                            execution_time_ms=execution_time * 1000
                        )
                        console.print(f"✅ [green]Local invocation tracking completed with safe fallback[/green]")
                    except Exception as e2:
                        console.print(f"❌ [red]Critical: Could not complete local invocation tracking: {str(e2)}[/red]")

                # NEW: Sync invocation completion to middleware
                if middleware_invocation_id:
                    try:
                        await self.middleware_sync.sync_invocation_complete(
                            middleware_invocation_id,
                            {
                                "output_data": serializable_output,
                                "execution_time_ms": execution_time * 1000
                            }
                        )
                    except Exception as e:
                        console.print(f"[yellow]Failed to sync completion to middleware: {e}[/yellow]")

                # Record in original agent_runs table for backward compatibility
                self.db_service.record_agent_run(
                    agent_id=agent_id,
                    input_data=request.input_data,
                    output_data=result_str,
                    success=True,
                    execution_time=execution_time,
                )

                console.print(
                    f"✅ Agent [cyan]{agent_id}[/cyan] execution completed successfully in "
                    f"{execution_time:.2f}s (invocation: {invocation_id}...)"
                )

                return AgentRunResponse(
                    success=True,
                    output_data=result_str,
                    error=None,
                    execution_time=execution_time,
                    agent_id=agent_id,
                )

            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                error_detail = f"Server error running agent {agent_id}: {str(e)}"
                self.log_execution_error(invocation_id, e)
                execution_time = time.time() - start_time

                # Complete local invocation tracking with error
                self.db_service.complete_invocation(
                    invocation_id=invocation_id,
                    error_detail=error_detail,
                    execution_time_ms=execution_time * 1000
                )

                # NEW: Sync invocation error to middleware
                if middleware_invocation_id:
                    try:
                        await self.middleware_sync.sync_invocation_complete(
                            middleware_invocation_id,
                            {
                                "error_detail": error_detail,
                                "execution_time_ms": execution_time * 1000
                            }
                        )
                    except Exception as sync_error:
                        console.print(f"⚠️ [yellow]Failed to sync error to middleware: {sync_error}[/yellow]")

                # Record in original agent_runs table for backward compatibility
                self.db_service.record_agent_run(
                    agent_id=agent_id,
                    input_data=request.input_data,
                    output_data=None,
                    success=False,
                    error_message=error_detail,
                    execution_time=execution_time,
                )

                console.print(f"💥 [red]{error_detail}[/red] (invocation: {invocation_id[:8]}...)")

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail
                )
        
        return run_agent

    # Add this method to show sync status in server info
    def get_server_info(self) -> dict:
        """Get server information including middleware sync status"""
        sync_status = self.middleware_sync.get_sync_status()
        
        return {
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}",
            "docs_url": f"http://{self.host}:{self.port}/docs",
            "status": "running",
            "server_type": "FastAPI",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_framework": self.agent_framework,
            "invocation_tracking": True,
            "middleware_sync": {
                "enabled": sync_status["sync_enabled"],
                "api_configured": sync_status["api_configured"],
                "middleware_available": sync_status["middleware_available"],
                "base_url": sync_status["base_url"]
            }
        }


    def _setup_fastapi_app(self):
        """Setup FastAPI app"""
        app = FastAPI(
            title=f"RunAgent API - {self.agent_name}",
            description=f"Agent ID: {self.agent_id}",
            version=self.agent_version,
        )

        # Setup CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app

    def _install_dependencies(self):
        """Install agent dependencies from requirements.txt if it exists"""
        req_txt_path = self.agent_path / "requirements.txt"
        if req_txt_path.exists():
            try:
                console.print(f"📦 Installing dependencies from {req_txt_path}")
                _ = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_txt_path],
                    capture_output=False,  # Shows output directly
                    check=True,
                )
                console.print("✅ Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                raise Exception(
                    f"Failed to install dependencies from {req_txt_path}: {str(e)}"
                )
                
                
    @staticmethod
    def from_id(agent_id: str) -> "LocalServer":
        """
        Create LocalServer instance from an agent ID.

        Args:
            agent_id: ID of the agent to serve

        Returns:
            LocalServer instance

        Raises:
            Exception: If agent not found in database
        """
        db_service = DBService()
        agent = db_service.get_agent(agent_id)

        if agent is None:
            raise Exception(f"Agent {agent_id} not found in local database")

        # Display existing agent information
        console.print(f"[yellow]Found agent by ID: {agent_id}[/yellow]")
        console.print(f"[cyan]Agent Details:[/cyan]")
        console.print(f"   • Agent ID: [bold magenta]{agent['agent_id']}[/bold magenta]")
        console.print(f"   • Path: [blue]{agent['agent_path']}[/blue]")
        console.print(f"   • Host: [blue]{agent['host']}[/blue]")
        console.print(f"   • Port: [blue]{agent['port']}[/blue]")
        console.print(f"   • Framework: [green]{agent['framework']}[/green]")
        console.print(f"   • Status: [yellow]{agent['status']}[/yellow]")
        console.print(f"   • Deployed: [dim]{agent['deployed_at']}[/dim]")
        console.print(f"   • Total Runs: [cyan]{agent['run_count']}[/cyan]")
        console.print(f"   • Success Rate: [green]{agent['success_count']}/{agent['run_count']}[/green]")
        
        if agent['last_run']:
            console.print(f"   • Last Run: [dim]{agent['last_run']}[/dim]")
        
        console.print(f"\n🔄 [green]Loading existing agent configuration[/green]")

        return LocalServer(
            db_service=db_service,
            agent_id=agent_id,
            agent_path=Path(agent["agent_path"]),
            port=agent["port"],
            host=agent["host"],
        )

    @staticmethod
    def from_path(
        agent_path: Path, port: int = None, host: str = "127.0.0.1"
    ) -> "LocalServer":
        """
        Create LocalServer instance from an agent path with smart port handling.
        Works with all frameworks including Letta (no special handling needed).

        Args:
            agent_path: Path to agent directory
            port: Preferred port (auto-allocated if None or unavailable)
            host: Preferred host (default: 127.0.0.1)

        Returns:
            LocalServer instance
        """
        db_service = DBService()
        agent_path = agent_path.resolve()

        # Get agent config to determine framework
        try:
            agent_config = get_agent_config(agent_path)
            framework = agent_config.framework
        except Exception as e:
            framework = detect_framework(agent_path)

        # Check if an agent from this path already exists
        existing_agent = db_service.get_agent_by_path(str(agent_path))
        
        if existing_agent:
            # Agent already exists - check if its port is available
            existing_host = existing_agent['host']
            existing_port = existing_agent['port']
            
            console.print(f"[yellow]Found existing agent for path: {agent_path}[/yellow]")
            console.print(f"[cyan]Agent Details:[/cyan]")
            console.print(f"   • Agent ID: [bold magenta]{existing_agent['agent_id']}[/bold magenta]")
            console.print(f"   • Host: [blue]{existing_host}[/blue]")
            console.print(f"   • Port: [blue]{existing_port}[/blue]")
            console.print(f"   • Framework: [green]{existing_agent['framework']}[/green]")
            console.print(f"   • Status: [yellow]{existing_agent['status']}[/yellow]")
            console.print(f"   • Deployed: [dim]{existing_agent['deployed_at']}[/dim]")
            console.print(f"   • Total Runs: [cyan]{existing_agent['run_count']}[/cyan]")
            console.print(f"   • Success Rate: [green]{existing_agent['success_count']}/{existing_agent['run_count']}[/green]")
            
            if existing_agent['last_run']:
                console.print(f"   • Last Run: [dim]{existing_agent['last_run']}[/dim]")
                        
            # Check if the existing port is available
            if PortManager.is_port_available(existing_host, existing_port):
                console.print(f"\n🔄 [green]Port {existing_port} is available - reusing existing agent configuration[/green]")
                
                return LocalServer(
                    agent_path=agent_path,
                    agent_id=existing_agent['agent_id'],
                    port=existing_port,
                    host=existing_host,
                    db_service=db_service,
                )
            else:
                # Port is in use - need to allocate a new one and update the database
                console.print(f"\n[yellow]Port {existing_port} is already in use - allocating new port[/yellow]")
                
                # Get currently used ports to avoid conflicts
                used_ports = PortManager.get_used_ports_from_db(db_service)
                
                # Allocate new address
                if port and PortManager.is_port_available(host, port):
                    new_host = host
                    new_port = port
                    console.print(f"Using preferred address: [blue]{new_host}:{new_port}[/blue]")
                else:
                    new_host, new_port = PortManager.allocate_unique_address(used_ports)
                
                # Update the existing agent's host/port in the database
                with db_service.db_manager.get_session() as session:
                    from runagent.sdk.db import Agent
                    agent_record = session.query(Agent).filter(Agent.agent_id == existing_agent['agent_id']).first()
                    if agent_record:
                        agent_record.host = new_host
                        agent_record.port = new_port
                        session.commit()
                        console.print(f"🔄 [green]Updated agent address in database: {new_host}:{new_port}[/green]")
                
                return LocalServer(
                    agent_path=agent_path,
                    agent_id=existing_agent['agent_id'],
                    port=new_port,
                    host=new_host,
                    db_service=db_service,
                )
        
        else:
            # No existing agent - create new one
            console.print(f"🆕 [green]Creating new agent for path: {agent_path}[/green]")
            console.print(f"📋 [cyan]Framework detected: [bold]{framework}[/bold][/cyan]")
            
            # Check database capacity
            capacity_info = db_service.get_database_capacity_info()
            if capacity_info["is_full"]:
                raise Exception(
                    "Database is full. Refer to our docs at "
                    "https://docs.runagent.ai/local-server for more information."
                )

            # Generate unique agent ID (same for all frameworks including Letta)
            agent_id = str(uuid.uuid4())
            
            # Add agent with automatic port allocation
            result = db_service.add_agent_with_auto_port(
                agent_id=agent_id,
                agent_path=str(agent_path),
                framework=framework.value if hasattr(framework, 'value') else str(framework),
                status="ready",
                preferred_host=host,
                preferred_port=port,  # Will auto-allocate if None or unavailable
            )
            
            if not result["success"]:
                raise Exception(f"Failed to add agent to database: {result['error']}")
            
            allocated_host = result["allocated_host"]
            allocated_port = result["allocated_port"]
            
            console.print(f"✅ [green]New agent created with ID: [bold magenta]{agent_id}[/bold magenta][/green]")
            console.print(f"🔌 [green]Allocated address: [bold blue]{allocated_host}:{allocated_port}[/bold blue][/green]")
            
            return LocalServer(
                agent_path=agent_path,
                agent_id=agent_id,
                port=allocated_port,  # Use allocated port
                host=allocated_host,  # Use allocated host
                db_service=db_service,
            )

    def _setup_routes(self):
        """Setup FastAPI routes - ENHANCED with invocation tracking"""

        @self.app.get("/api/v1", response_model=AgentInfo)
        async def home():
            """Root endpoint showing server info and available agents"""
            try:
                config = self.agent_config.dict()
                config.pop("env_vars")
                return AgentInfo(
                    message=f"RunAgent API - {self.agent_name}({self.agent_id})",
                    version=self.agent_version,
                    host=self.host,
                    port=self.port,
                    config=config,
                    endpoints={
                        "GET /": "Agent info",
                        "GET /health": "Health check",
                        "POST /api/v1/agents/{agent_id}/execute/{entrypoint}": "Execute agent",
                        "GET /api/v1/agents/{agent_id}/invocations": "Get invocation history",
                        "GET /api/v1/agents/{agent_id}/invocations/stats": "Get invocation stats",
                    },
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get server info: {str(e)}",
                )

        @self.app.get("/api/v1/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "server": "RunAgent FastAPI Local Server",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "version": "1.0.0",
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "framework": self.agent_framework,
            }
        
        @self.app.get(f"/api/v1/agents/{self.agent_id}/architecture")
        async def get_agent_architecture():
            """Get agent architecture endpoint"""
            return {
                "agent_id": self.agent_id,
                "entrypoints": [ep.dict() for ep in self.agent_config.agent_architecture.entrypoints]
            }

        # NEW: Invocation history endpoints
        @self.app.get(f"/api/v1/agents/{self.agent_id}/invocations")
        async def get_agent_invocations(limit: int = 50, status: str = None):
            """Get invocation history for this agent"""
            try:
                invocations = self.db_service.list_invocations(
                    agent_id=self.agent_id,
                    status=status,
                    limit=limit
                )
                return {
                    "agent_id": self.agent_id,
                    "invocations": invocations,
                    "total_count": len(invocations)
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get invocations: {str(e)}",
                )

        @self.app.get(f"/api/v1/agents/{self.agent_id}/invocations/stats")
        async def get_agent_invocation_stats():
            """Get invocation statistics for this agent"""
            try:
                stats = self.db_service.get_invocation_stats(agent_id=self.agent_id)
                return {
                    "agent_id": self.agent_id,
                    "stats": stats
                }
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get invocation stats: {str(e)}",
                )

        @self.app.get("/api/v1/invocations/{invocation_id}")
        async def get_invocation_details(invocation_id: str):
            """Get details of a specific invocation"""
            try:
                invocation = self.db_service.get_invocation(invocation_id)
                if not invocation:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Invocation {invocation_id} not found"
                    )
                return invocation
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get invocation: {str(e)}",
                )

        # Setup dynamic entrypoint routes with invocation tracking
        for entrypoint in self.agent_architecture.entrypoints:
            if entrypoint.tag.endswith("_stream"):
                continue

            runner = self.agentic_executor.get_runner(entrypoint)
            
            self.app.post(
                f"/api/v1/agents/{self.agent_id}/execute/{entrypoint.tag}",
                response_model=AgentRunResponse
            )(self.create_endpoint_handler_with_tracking(runner, self.agent_id, entrypoint.tag))


    def _convert_to_serializable(self, obj):
        """Convert objects to JSON-serializable format"""
        try:
            # Try direct JSON serialization first
            import json
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # Handle common non-serializable objects
            if hasattr(obj, '__dict__'):
                # Objects with __dict__ (like ChatResult, TextEvent, etc.)
                return {
                    "type": type(obj).__name__,
                    "data": {k: self._convert_to_serializable(v) for k, v in obj.__dict__.items()}
                }
            elif hasattr(obj, '_asdict'):
                # Named tuples
                return {
                    "type": type(obj).__name__,
                    "data": obj._asdict()
                }
            elif hasattr(obj, 'dict'):
                # Pydantic models (v1)
                try:
                    return obj.dict()
                except:
                    return {"type": type(obj).__name__, "repr": repr(obj)[:500]}
            elif hasattr(obj, 'model_dump'):
                # Pydantic models (v2)
                try:
                    return obj.model_dump()
                except:
                    return {"type": type(obj).__name__, "repr": repr(obj)[:500]}
            elif isinstance(obj, (list, tuple)):
                # Handle lists/tuples recursively
                return [self._convert_to_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                # Handle dictionaries recursively
                return {k: self._convert_to_serializable(v) for k, v in obj.items()}
            else:
                # Fallback to string representation
                return {
                    "type": type(obj).__name__,
                    "repr": repr(obj)[:500],  # Limit length
                    "str": str(obj)[:500]     # Limit length
                }

    def _setup_websocket_routes(self):
        """Setup WebSocket routes with invocation tracking"""
        for entrypoint in self.agent_architecture.entrypoints:
            if not entrypoint.tag.endswith("_stream"):
                continue

            stream_runner = self.agentic_executor.get_stream_runner(entrypoint)

            # Create a separate function for each entrypoint with invocation tracking
            def make_websocket_handler_with_tracking(runner, entrypoint_tag):  # Factory function
                @self.app.websocket(f"/api/v1/agents/{self.agent_id}/execute/{entrypoint_tag}")
                async def websocket_endpoint(websocket: WebSocket, agent_id: str = self.agent_id):
                    await self.websocket_handler.handle_agent_stream_with_tracking(
                        websocket, agent_id, runner, entrypoint_tag, self.db_service
                    )
                return websocket_endpoint
            
            make_websocket_handler_with_tracking(stream_runner, entrypoint.tag)

    def extract_endpoints(self):
        """Extract all endpoints from the FastAPI app"""
        endpoints = []

        for route in self.app.routes:
            if len(getattr(route, "methods", list())) == 1 and hasattr(route, "path"):
                # Get the endpoint function
                endpoint_func = route.endpoint if hasattr(route, "endpoint") else None

                # Extract description from docstring or route description
                description = ""
                if endpoint_func and endpoint_func.__doc__:
                    description = endpoint_func.__doc__.strip()
                elif hasattr(route, "description") and route.description:
                    description = route.description

                endpoints.append(
                    {
                        "path": route.path,
                        "methods": list(route.methods),
                        "name": route.name,
                        "description": description,
                        "function_name": (
                            endpoint_func.__name__ if endpoint_func else None
                        ),
                    }
                )

        return endpoints

    def start(self, debug: bool = False):
        """Start the FastAPI server with FIXED middleware sync timing"""
        try:
            # STEP 1: Log server startup to LOCAL database first
            if hasattr(self, 'agent_logger'):
                self.agent_logger.info("FastAPI server starting...")
                self.agent_logger.info(f"Debug mode: {'ON' if debug else 'OFF'}")
                self.agent_logger.info(f"Server URL: http://{self.host}:{self.port}")
                self.agent_logger.info(f"Docs URL: http://{self.host}:{self.port}/docs")
            
            # STEP 2: Sync agent to middleware BEFORE starting server (BLOCKING)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                sync_success = loop.run_until_complete(self._sync_agent_to_middleware_and_wait())
            finally:
                loop.close()
            
            # STEP 3: Print sync status
            if self.middleware_sync and self.middleware_sync.sync_enabled:
                console.print("🔄 [cyan]Middleware Sync Status:[/cyan]")
                if sync_success:
                    console.print("   Status: ✅ ENABLED & SYNCED")
                else:
                    console.print("   Status: ⚠️ ENABLED BUT SYNC FAILED")
                    console.print("Local logs will be stored locally only")
            else:
                console.print("[yellow]Middleware Sync Status:[/yellow]")
                console.print("   Status: ❌ DISABLED")
                console.print("   💡 Configure API key to enable sync")
                
                if hasattr(self, 'agent_logger'):
                    self.agent_logger.warning("Middleware sync disabled - logs stored locally only")

            # # Print server info
            # console.print(
            #     f"🌐 Server URL: [bold blue]http://{self.host}:{self.port}[/bold blue]"
            # )

            # Print available endpoints
            console.print("\n📋 Available endpoints:")
            endpoints = self.extract_endpoints()
            for endpoint in endpoints:
                route_path = endpoint["path"]
                route_methods = endpoint["methods"][0]
                route_description = endpoint["description"]
                console.print(
                    f"   • [cyan]{route_methods}  {route_path}[/cyan] - {route_description}"
                )

            console.print("[yellow]Use Ctrl+C to stop the server[/yellow]")

            # Print debug status
            debug_color = "green" if debug else "red"
            debug_status = "ON" if debug else "OFF"
            console.print(
                f"🔧 Debug mode: [{debug_color}]{debug_status}[/{debug_color}]"
            )

            # Print docs URL
            console.print(
                f"📖 API Docs: [link]http://{self.host}:{self.port}/docs[/link]\n"
            )
            # Print agent ID
            console.print(f"🆔 Agent ID: [bold magenta]{self.agent_id}[/bold magenta]")

            # Print invocation tracking info
            console.print(f"📊 Invocation tracking: [green]ENABLED[/green]")
            console.print(f"   • View stats: [cyan]GET /api/v1/agents/{self.agent_id}/invocations/stats[/cyan]")
            console.print(f"   • View history: [cyan]GET /api/v1/agents/{self.agent_id}/invocations[/cyan]")

            # Log that server is about to start
            if hasattr(self, 'agent_logger'):
                self.agent_logger.info("Starting uvicorn server...")
                if sync_success:
                    self.agent_logger.info("Agent synced to middleware - full sync mode enabled")
                else:
                    self.agent_logger.info("Agent sync failed - running in local-only mode")

            # Start uvicorn server
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="debug" if debug else "info",
                access_log=debug,
                reload=False,  # Disable auto-reload for stability
            )

        except OSError as e:
            error_msg = str(e)
            if "Address already in use" in error_msg:
                console.print(f"💥 [red]Port {self.port} is already in use![/red]")
                console.print(
                    f"Try using a different port: "
                    f"[cyan]runagent serve --port {self.port + 1}[/cyan]"
                )
                console.print("Or stop the existing server and try again")
                
                if hasattr(self, 'agent_logger'):
                    self.agent_logger.error(f"Port {self.port} already in use")
            else:
                console.print(f"[red]Network error: {error_msg}[/red]")
                if hasattr(self, 'agent_logger'):
                    self.agent_logger.error(f"Network error: {error_msg}")
            raise
        except KeyboardInterrupt:
            console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
            
            # Log shutdown
            if hasattr(self, 'agent_logger'):
                self.agent_logger.info("Server shutdown initiated by user")
            
            self.shutdown_logging()
            
            # Clean up middleware sync on shutdown
            if self.middleware_sync and hasattr(self.middleware_sync, 'enabled') and self.middleware_sync.enabled:
                console.print("🧹 [cyan]Cleaning up middleware sync...[/cyan]")
                if hasattr(self.middleware_sync, 'remove_agent'):
                    self.middleware_sync.remove_agent(self.agent_id)
        except Exception as e:
            error_msg = f"Server error: {str(e)}"
            console.print(f"💥 [red]{error_msg}[/red]")
            
            if hasattr(self, 'agent_logger'):
                self.agent_logger.error(error_msg, exc_info=True)
            raise

    def get_server_info(self) -> dict:
        """Get server information"""
        return {
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}",
            "docs_url": f"http://{self.host}:{self.port}/docs",
            "status": "running",
            "server_type": "FastAPI",
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_framework": self.agent_framework,
            "invocation_tracking": True,
        }

    def _ensure_agent_in_database(self):
        """Ensure regular agent is in database"""
        agent = self.db_service.get_agent(self.agent_id)
        if not agent:
            result = self.db_service.add_agent(
                agent_id=self.agent_id,
                agent_path=str(self.agent_path),
                host=self.host,
                port=self.port,
                framework=self.agent_framework,
            )
            if not result["success"]:
                console.print(f"[red]Failed to add agent to database: {result['error']}[/red]")
                raise Exception(f"Failed to add agent to database: {result['error']}")

    def _update_letta_agent_id_in_db(self):
        """Update database with actual Letta agent ID after initialization"""
        try:
            # Import the agent module to trigger Letta agent creation
            from runagent.utils.imports import PackageImporter
            importer = PackageImporter()
            
            # Import the agent module to initialize Letta agent
            agent_module = importer.resolve_import(
                self.agent_path / "agent.py", 
                "_get_letta_agent_id"
            )
            
            # Get the actual Letta agent ID
            actual_letta_agent_id = agent_module()
            
            if actual_letta_agent_id and actual_letta_agent_id != self.agent_id:
                console.print(f"🔄 Updating database with Letta agent ID: {actual_letta_agent_id}")
                
                # Update the agent ID in database
                with self.db_service.db_manager.get_session() as session:
                    from runagent.sdk.db import Agent
                    
                    # Update existing record
                    agent_record = session.query(Agent).filter(
                        Agent.agent_id == self.agent_id
                    ).first()
                    
                    if agent_record:
                        agent_record.agent_id = actual_letta_agent_id
                        session.commit()
                        
                        # Update our internal agent ID
                        self.agent_id = actual_letta_agent_id
                        console.print(f"✅ Database updated with Letta agent ID: {self.agent_id}")
                    else:
                        # Create new record with Letta agent ID
                        new_agent = Agent(
                            agent_id=actual_letta_agent_id,
                            agent_path=str(self.agent_path),
                            host=self.host,
                            port=self.port,
                            framework=self.agent_framework,
                            status="deployed",
                        )
                        session.add(new_agent)
                        session.commit()
                        self.agent_id = actual_letta_agent_id
                        console.print(f"✅ Created database record with Letta agent ID: {self.agent_id}")
            
        except Exception as e:
            console.print(f"⚠️ Could not update Letta agent ID in database: {e}")

            
    def _setup_logging(self):
        """Setup enhanced logging with database integration - FIXED with sync check"""
        try:
            # Create custom logger for this agent
            self.agent_logger = logging.getLogger(f'runagent_agent_{self.agent_id}')
            self.agent_logger.setLevel(logging.DEBUG)
            
            # Remove existing handlers to avoid duplicates
            for handler in self.agent_logger.handlers[:]:
                self.agent_logger.removeHandler(handler)
            
            # Add database handler with sync-aware middleware
            try:
                from runagent.utils.logs import DatabaseLogHandler
                self.db_handler = DatabaseLogHandler(
                    self.db_service, 
                    self.agent_id, 
                    getattr(self, 'middleware_sync', None),
                    sync_check_callback=lambda: getattr(self, 'agent_synced_to_middleware', False)  # NEW
                )
                self.db_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self.agent_logger.addHandler(self.db_handler)
            except Exception as e:
                console.print(f"⚠️ [yellow]Could not setup database logging: {e}[/yellow]")
            
            # Also keep console output
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.agent_logger.addHandler(console_handler)
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Enhanced logging setup failed: {e}[/yellow]")


    def log_execution_start(self, execution_id: str, entrypoint_tag: str):
        """Log execution start with execution context"""
        extra = {'execution_id': execution_id}
        if hasattr(self, 'agent_logger'):
            self.agent_logger.info(
                f"Starting execution {execution_id[:8]}... for entrypoint '{entrypoint_tag}'", 
                extra=extra
            )
        else:
            console.print(f"🚀 Starting execution {execution_id[:8]}... for entrypoint '{entrypoint_tag}'")
    
    def log_execution_complete(self, execution_id: str, success: bool, execution_time: float):
        """Log execution completion"""
        extra = {'execution_id': execution_id}
        if hasattr(self, 'agent_logger'):
            if success:
                self.agent_logger.info(
                    f"Execution {execution_id[:8]}... completed successfully in {execution_time:.2f}s", 
                    extra=extra
                )
            else:
                self.agent_logger.error(
                    f"Execution {execution_id[:8]}... failed after {execution_time:.2f}s", 
                    extra=extra
                )
        else:
            status = "completed successfully" if success else "failed"
            console.print(f"✅ Execution {execution_id[:8]}... {status} in {execution_time:.2f}s")
    
    def log_execution_error(self, execution_id: str, error: Exception):
        """Log execution error"""
        extra = {'execution_id': execution_id}
        if hasattr(self, 'agent_logger'):
            self.agent_logger.error(
                f"Execution {execution_id[:8]}... error: {str(error)}", 
                extra=extra, 
                exc_info=True
            )
        else:
            console.print(f"💥 [red]Execution {execution_id[:8]}... error: {str(error)}[/red]")

    def shutdown_logging(self):
        """Properly shutdown logging and flush remaining logs"""
        try:
            if hasattr(self, 'db_handler'):
                self.db_handler.close()
            if hasattr(self, 'agent_logger'):
                for handler in self.agent_logger.handlers[:]:
                    handler.close()
                    self.agent_logger.removeHandler(handler)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error during logging shutdown: {e}[/yellow]")

    def shutdown_logging(self):
        """Properly shutdown logging and flush remaining logs"""
        try:
            if hasattr(self, 'db_handler'):
                self.db_handler.close()
            if hasattr(self, 'agent_logger'):
                for handler in self.agent_logger.handlers[:]:
                    handler.close()
                    self.agent_logger.removeHandler(handler)
        except Exception as e:
            console.print(f"⚠️ [yellow]Error during logging shutdown: {e}[/yellow]")

    def log_raw(self, level: str, message: str, execution_id: str = None):
        """Simple method to log raw messages - use this for all server logs"""
        if hasattr(self, 'agent_logger'):
            extra = {'execution_id': execution_id} if execution_id else {}
            log_method = getattr(self.agent_logger, level.lower(), self.agent_logger.info)
            log_method(message, extra=extra)
        else:
            # Fallback to console if logger not available
            level_colors = {
                'info': 'cyan',
                'warning': 'yellow', 
                'error': 'red',
                'debug': 'dim'
            }
            color = level_colors.get(level.lower(), 'white')
            console.print(f"[{color}]{level.upper()}: {message}[/{color}]")

    def log_info(self, message: str, execution_id: str = None):
        """Log info message"""
        self.log_raw('info', message, execution_id)

    def log_warning(self, message: str, execution_id: str = None):
        """Log warning message"""
        self.log_raw('warning', message, execution_id)

    def log_error(self, message: str, execution_id: str = None):
        """Log error message"""
        self.log_raw('error', message, execution_id)

    def log_debug(self, message: str, execution_id: str = None):
        """Log debug message"""
        self.log_raw('debug', message, execution_id)

    def __repr__(self):
        return f"LocalServer(agent_id='{self.agent_id}', host='{self.host}', port={self.port})"

    def __str__(self):
        return f"RunAgent Local Server - {self.agent_name} ({self.agent_id}) at http://{self.host}:{self.port}"