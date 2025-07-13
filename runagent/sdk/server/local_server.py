# runagent/server/local_server.py
import json
import os
import subprocess
import sys
import time
import uuid
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

console = Console()


class LocalServer:
    """FastAPI-based local server for testing deployed agents"""

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

        self.agent_config = get_agent_config(agent_path)

        self.agent_name = self.agent_config.agent_name
        self.agent_version = self.agent_config.version
        self.agent_framework = self.agent_config.framework
        self.agent_architecture = self.agent_config.agent_architecture  

        # Install dependencies if requirements.txt exists
        self._install_dependencies()

        # Set environment variables from agent config
        for key, value in self.agent_config.env_vars.items():
            os.environ[key] = str(value)

        self.agentic_executor = get_executor(
            self.agent_path, self.agent_framework, self.agent_architecture.entrypoints
        )

        # Handle agent setup (simplified - no special Letta handling needed)
        self._ensure_agent_in_database()

        self.websocket_handler = AgentWebSocketHandler(self.db_service)
        self.start_time = time.time()

        self.app = self._setup_fastapi_app()
        self._setup_websocket_routes()
        self._setup_routes()



    def _setup_fastapi_app(self):
        """Setup FastAPI app"""
        app = FastAPI(
            title=f"RunAgent API - {self.agent_name}",
            description=f"Agend ID: {self.agent_id}",
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
                _ = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_txt_path],
                    capture_output=False,  # Shows output directly
                    check=True,
                )
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
        console.print(f"🔍 [yellow]Found agent by ID: {agent_id}[/yellow]")
        console.print(f"📋 [cyan]Agent Details:[/cyan]")
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
        import uuid
        from runagent.utils.port import PortManager
        from runagent.utils.agent import detect_framework, get_agent_config

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
            
            console.print(f"🔍 [yellow]Found existing agent for path: {agent_path}[/yellow]")
            console.print(f"📋 [cyan]Agent Details:[/cyan]")
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
                console.print(f"\n⚠️ [yellow]Port {existing_port} is already in use - allocating new port[/yellow]")
                
                # Get currently used ports to avoid conflicts
                used_ports = PortManager.get_used_ports_from_db(db_service)
                
                # Allocate new address
                if port and PortManager.is_port_available(host, port):
                    new_host = host
                    new_port = port
                    console.print(f"🎯 Using preferred address: [blue]{new_host}:{new_port}[/blue]")
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
                framework=framework,
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
            
            if framework == "letta":
                console.print(f"🤖 [yellow]Letta agent will be created when first called[/yellow]")
                console.print(f"💡 [dim]Make sure Letta server is running: letta server[/dim]")
            
            return LocalServer(
                agent_path=agent_path,
                agent_id=agent_id,
                port=allocated_port,  # Use allocated port
                host=allocated_host,  # Use allocated host
                db_service=db_service,
            )

    def _setup_routes(self):
        """Setup FastAPI routes"""

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
                        "POST /api/v1/agents/{agent_id}/run": "Run an agent",
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
            }
        @self.app.get(f"/api/v1/agents/{self.agent_id}/architecture")
        async def get_agent_architecture():
            """Health check endpoint"""
            return {
                "agent_id": self.agent_id,
                "entrypoints": self.agent_config.agent_architecture.entrypoints
            }

        # Then in your loop:
        for entrypoint in self.agent_architecture.entrypoints:
            if entrypoint.tag.endswith("_stream"):
                continue

            runner = self.agentic_executor.get_runner(entrypoint)
            
            self.app.post(
                f"/api/v1/agents/{self.agent_id}/execute/{entrypoint.tag}",
                response_model=AgentRunResponse
            )(self.create_endpoint_handler(runner, self.agent_id))

    def create_endpoint_handler(self, runner, agent_id):
        async def run_agent(request: AgentRunRequest):
            """Run a deployed agent"""
            start_time = time.time()

            try:
                console.print(f"🚀 Running agent: [cyan]{agent_id}[/cyan]")

                result = runner(
                    *request.input_data.input_args, **request.input_data.input_kwargs
                )

                result_str = self.serializer.serialize_object(result)
                execution_time = time.time() - start_time

                # Record successful run in database
                self.db_service.record_agent_run(
                    agent_id=agent_id,
                    input_data=request.input_data,
                    output_data=result_str,
                    success=True,
                    execution_time=execution_time,
                )

                console.print(
                    f"✅ Agent [cyan]{agent_id}[/cyan] execution completed successfully in "
                    f"{execution_time:.2f}s"
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
                error_msg = f"Server error running agent {agent_id}: {str(e)}"
                execution_time = time.time() - start_time

                # Record failed run in database
                self.db_service.record_agent_run(
                    agent_id=agent_id,
                    input_data=request.input_data,
                    output_data=None,
                    success=False,
                    error_message=error_msg,
                    execution_time=execution_time,
                )

                console.print(f"💥 [red]{error_msg}[/red]")

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
                )
        
        return run_agent

    # def _setup_websocket_routes(self):
    #     """Add WebSocket routes to your existing FastAPI app"""
    #     for entrypoint in self.agent_architecture.entrypoints:

    #         if not entrypoint.tag.endswith("_stream"):
    #             continue

    #         stream_runner = self.agentic_executor.get_stream_runner(entrypoint)

    #         @self.app.websocket("/api/v1/agents/{agent_id}" + f"/execute/{entrypoint.tag}")
    #         async def run_agent_stream(websocket: WebSocket, agent_id: str):
    #             """WebSocket endpoint for agent streaming"""
    #             await self.websocket_handler.handle_agent_stream(
    #                 websocket, agent_id, stream_runner
    #             )

    # def create_websocket_handler(self, stream_runner, entrypoint_tag):
    #     async def run_agent_stream(websocket: WebSocket, agent_id: str):
    #         """WebSocket endpoint for agent streaming"""
    #         await self.websocket_handler.handle_agent_stream(
    #             websocket, agent_id, stream_runner
    #         )
    #     return run_agent_stream

    # def _setup_websocket_routes(self):
    #     """Add WebSocket routes to your existing FastAPI app"""

    #     for entrypoint in self.agent_architecture.entrypoints:
    #         if not entrypoint.tag.endswith("_stream"):
    #             continue

    #         stream_runner = self.agentic_executor.get_stream_runner(entrypoint)
            
    #         self.app.websocket(
    #             f"/api/v1/agents/{self.agent_id}/execute/{entrypoint.tag}"
    #         )(self.create_websocket_handler(stream_runner, entrypoint.tag))
            
    def _setup_websocket_routes(self):
        for entrypoint in self.agent_architecture.entrypoints:
            if not entrypoint.tag.endswith("_stream"):
                continue

            stream_runner = self.agentic_executor.get_stream_runner(entrypoint)

            # Create a separate function for each entrypoint
            def make_websocket_handler(runner):  # ← Factory function
                @self.app.websocket(f"/api/v1/agents/{self.agent_id}/execute/{entrypoint.tag}")
                async def websocket_endpoint(websocket: WebSocket, agent_id: str = self.agent_id):
                    await self.websocket_handler.handle_agent_stream(websocket, agent_id, runner)
                return websocket_endpoint
            
            make_websocket_handler(stream_runner)

    def extract_endpoints(self):
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
        """Start the FastAPI server"""
        try:
            # Print server info
            console.print(
                f"🌐 Server URL: [bold blue]http://{self.host}:{self.port}[/bold blue]"
            )

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

            console.print("\n💡 [yellow]Use Ctrl+C to stop the server[/yellow]")

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
            if "Address already in use" in str(e):
                console.print(f"💥 [red]Port {self.port} is already in use![/red]")
                console.print(
                    f"💡 Try using a different port: "
                    f"[cyan]runagent serve --port {self.port + 1}[/cyan]"
                )
                console.print("💡 Or stop the existing server and try again")
            else:
                console.print(f"💥 [red]Network error: {str(e)}[/red]")
            raise
        except KeyboardInterrupt:
            console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            console.print(f"💥 [red]Server error: {str(e)}[/red]")
            raise

    def get_server_info(self) -> dict:
        """Get server information"""
        return {
            "host": self.host,
            "port": self.port,
            "deployments_dir": str(self.deployments_dir.absolute()),
            "url": f"http://{self.host}:{self.port}",
            "docs_url": f"http://{self.host}:{self.port}/docs",
            "status": "running",
            "server_type": "FastAPI",
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
