# runagent/server/local_server.py
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from rich.console import Console

console = Console()

# Pydantic Models
class AgentRunRequest(BaseModel):
    """Request model for agent execution"""
    messages: Optional[List[Dict[str, str]]] = Field(default=[], description="List of messages")
    config: Optional[Dict[str, Any]] = Field(default={}, description="Configuration parameters")
    context: Optional[Dict[str, Any]] = Field(default={}, description="Additional context")

class AgentRunResponse(BaseModel):
    """Response model for agent execution"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    agent_id: str

class ServerInfo(BaseModel):
    """Server information model"""
    message: str
    version: str
    host: str
    port: int
    total_agents: int
    capacity: Dict[str, Any]
    available_agents: Dict[str, Dict[str, Any]]
    endpoints: Dict[str, str]

class CapacityInfo(BaseModel):
    """Database capacity information"""
    current_count: int
    max_capacity: int
    remaining_slots: int
    is_full: bool
    agents: List[Dict[str, Any]]

class LocalServer:
    """FastAPI-based local server for testing deployed agents"""
    
    def __init__(self, port: int = 8450, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.app = FastAPI(
            title="RunAgent Local Server",
            description="FastAPI-based local server for testing deployed AI agents",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self.deployments_dir = Path("deployments")
        self.start_time = time.time()
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize database when server starts
        self._init_database()
        
        # Setup routes
        self._setup_routes()
    
    def _init_database(self):
        """Initialize database when server starts"""
        try:
            from runagent.client.local_client import LocalClient
            
            # Create local client with auto-init
            console.print("🚀 Initializing RunAgent Local Server...")
            
            # This will create the database file
            from runagent.client.local_db import LocalDatabase
            db = LocalDatabase(auto_init=True)
            
            console.print("✅ Database ready for agent deployments")
            
        except Exception as e:
            console.print(f"⚠️ [yellow]Database initialization warning: {str(e)}[/yellow]")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_model=ServerInfo)
        async def home():
            """Root endpoint showing server info and available agents"""
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                
                # Get agents and capacity info
                agents_result = local_client.list_local_agents()
                capacity_info = local_client.get_capacity_info()
                
                available_agents = {}
                if agents_result.get('success'):
                    agents = agents_result.get('agents', [])
                    for agent in agents:
                        agent_id = agent.get('agent_id')
                        if agent_id:
                            available_agents[agent_id] = {
                                "endpoint": f"/agents/{agent_id}/run",
                                "status": agent.get('status', 'unknown'),
                                "framework": agent.get('framework', 'unknown'),
                                "deployed_at": agent.get('deployed_at'),
                                "exists": agent.get('exists', False)
                            }
                
                return ServerInfo(
                    message="RunAgent FastAPI Local Server",
                    version="1.0.0",
                    host=self.host,
                    port=self.port,
                    total_agents=len(available_agents),
                    capacity=capacity_info,
                    available_agents=available_agents,
                    endpoints={
                        "GET /": "Server info and agent list",
                        "POST /agents/{agent_id}/run": "Run an agent",
                        "GET /agents/{agent_id}/status": "Get agent status",
                        "GET /agents/{agent_id}/info": "Get detailed agent info",
                        "GET /agents": "List all agents",
                        "GET /capacity": "Get database capacity info",
                        "GET /health": "Health check",
                        "GET /stats": "Server statistics",
                        "GET /docs": "API documentation"
                    }
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get server info: {str(e)}"
                )
        
        @self.app.post("/agents/{agent_id}/run", response_model=AgentRunResponse)
        async def run_agent(agent_id: str, request: AgentRunRequest):
            """Run a deployed agent"""
            try:
                from runagent.client.local_client import LocalClient
                
                console.print(f"🚀 Running agent: [cyan]{agent_id}[/cyan]")
                
                # Prepare input data
                input_data = {
                    "messages": request.messages,
                    "config": request.config,
                    "context": request.context
                }
                
                # Log the request
                console.print(f"📥 Input: {json.dumps(input_data, indent=2)[:200]}...")
                
                start_time = time.time()
                
                # Initialize local client and run agent
                local_client = LocalClient()
                result = local_client.run_agent(agent_id, input_data)
                
                execution_time = time.time() - start_time
                
                # Log the response
                if result.get('success'):
                    console.print(f"✅ Agent [cyan]{agent_id}[/cyan] completed successfully in {execution_time:.2f}s")
                else:
                    console.print(f"❌ Agent [cyan]{agent_id}[/cyan] failed: {result.get('error')}")
                
                return AgentRunResponse(
                    success=result.get('success', False),
                    result=result.get('result'),
                    error=result.get('error'),
                    execution_time=execution_time,
                    agent_id=agent_id
                )
                
            except Exception as e:
                error_msg = f"Server error running agent {agent_id}: {str(e)}"
                console.print(f"💥 [red]{error_msg}[/red]")
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )
        
        @self.app.get("/agents/{agent_id}/status")
        async def get_agent_status(agent_id: str):
            """Get agent status"""
            try:
                from runagent.client.local_client import LocalClient
                
                local_client = LocalClient()
                agent_info_result = local_client.get_agent_info(agent_id)
                
                if not agent_info_result.get('success'):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=agent_info_result.get('error', f'Agent {agent_id} not found')
                    )
                
                agent_info = agent_info_result.get('agent_info', {})
                
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "status": agent_info.get('status', 'unknown'),
                    "framework": agent_info.get('framework'),
                    "deployed_at": agent_info.get('deployed_at'),
                    "deployment_exists": agent_info.get('deployment_exists', False),
                    "source_exists": agent_info.get('source_exists', False),
                    "local": True,
                    "endpoint": f"http://{self.host}:{self.port}/agents/{agent_id}/run",
                    "stats": agent_info.get('stats', {})
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Status check failed: {str(e)}"
                )
        
        @self.app.get("/agents/{agent_id}/info")
        async def get_agent_info(agent_id: str):
            """Get detailed agent information"""
            try:
                from runagent.client.local_client import LocalClient
                
                local_client = LocalClient()
                result = local_client.get_agent_info(agent_id)
                
                if not result.get('success'):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=result.get('error', f'Agent {agent_id} not found')
                    )
                
                return {
                    "success": True,
                    "agent_info": result.get('agent_info')
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get agent info: {str(e)}"
                )
        
        @self.app.get("/agents")
        async def list_agents():
            """List all deployed agents"""
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                result = local_client.list_local_agents()
                
                if result.get('success'):
                    return {
                        "success": True,
                        "agents": result.get('agents', []),
                        "total": len(result.get('agents', [])),
                        "capacity": local_client.get_capacity_info()
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get('error', 'Failed to list agents'),
                        "agents": []
                    }
                    
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list agents: {str(e)}"
                )
        
        @self.app.get("/capacity", response_model=CapacityInfo)
        async def get_capacity():
            """Get database capacity information"""
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                capacity_info = local_client.get_capacity_info()
                
                return CapacityInfo(**capacity_info)
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get capacity info: {str(e)}"
                )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "server": "RunAgent FastAPI Local Server",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "version": "1.0.0"
            }
        
        @self.app.get("/stats")
        async def get_server_stats():
            """Get comprehensive server statistics"""
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                
                # Get database stats
                db_stats = local_client.get_database_stats()
                capacity_info = local_client.get_capacity_info()
                
                # Calculate uptime
                uptime_seconds = time.time() - self.start_time
                uptime_hours = uptime_seconds / 3600
                
                return {
                    "success": True,
                    "server_info": {
                        "host": self.host,
                        "port": self.port,
                        "url": f"http://{self.host}:{self.port}",
                        "uptime_seconds": uptime_seconds,
                        "uptime_hours": round(uptime_hours, 2),
                        "version": "1.0.0",
                        "server_type": "FastAPI"
                    },
                    "database_stats": db_stats,
                    "capacity_info": capacity_info,
                    "endpoints_count": len(self.app.routes)
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get server stats: {str(e)}"
                )
        
        @self.app.delete("/agents/{agent_id}")
        async def delete_agent_files(agent_id: str):
            """Delete agent files (database entry preserved due to no-deletion policy)"""
            try:
                from runagent.client.local_client import LocalClient
                
                local_client = LocalClient()
                result = local_client.delete_agent(agent_id)
                
                if result.get('success'):
                    return {
                        "success": True,
                        "message": result.get('message'),
                        "note": result.get('note'),
                        "warning": "Database entry preserved - agent slot still used"
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=result.get('error')
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete agent files: {str(e)}"
                )
        
        @self.app.get("/agents/{agent_id}/logs")
        async def get_agent_logs(agent_id: str, limit: int = 50):
            """Get execution logs for an agent"""
            try:
                from runagent.client.local_client import LocalClient
                
                local_client = LocalClient()
                result = local_client.get_agent_logs(agent_id, limit)
                
                if result.get('success'):
                    return result
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=result.get('error')
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get agent logs: {str(e)}"
                )
    
    def start(self, debug: bool = False):
        """Start the FastAPI server"""
        try:
            # Ensure deployments directory exists
            self.deployments_dir.mkdir(exist_ok=True)
            
            console.print(f"🌐 Server URL: [bold blue]http://{self.host}:{self.port}[/bold blue]")
            console.print(f"📁 Deployments directory: [blue]{self.deployments_dir.absolute()}[/blue]")
            
            # Check for existing agents
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                
                agents_result = local_client.list_local_agents()
                capacity_info = local_client.get_capacity_info()
                
                if agents_result.get('success'):
                    agent_count = len(agents_result.get('agents', []))
                    console.print(f"📊 Agents: {agent_count}/5 slots used")
                    
                    if capacity_info.get('is_full'):
                        console.print(f"⚠️ [yellow]Database at full capacity![/yellow]")
                    elif agent_count > 0:
                        console.print(f"💚 {capacity_info.get('remaining_slots', 0)} slots available")
                    else:
                        console.print("📊 No agents currently deployed")
                        
                else:
                    console.print("📊 Could not check existing agents")
            except:
                console.print("📊 Database ready for first deployment")
            
            console.print(f"\n📋 Available endpoints:")
            console.print(f"   • [cyan]GET  /[/cyan] - Server info and agents overview")
            console.print(f"   • [cyan]GET  /agents[/cyan] - List all agents")
            console.print(f"   • [cyan]GET  /agents/{{id}}[/cyan] - Get agent info")
            console.print(f"   • [cyan]POST /agents/{{id}}/run[/cyan] - Run agent")
            console.print(f"   • [cyan]GET  /agents/{{id}}/status[/cyan] - Agent status")
            console.print(f"   • [cyan]GET  /agents/{{id}}/logs[/cyan] - Agent execution logs")
            console.print(f"   • [cyan]DELETE /agents/{{id}}[/cyan] - Delete agent files (DB preserved)")
            console.print(f"   • [cyan]GET  /capacity[/cyan] - Database capacity info")
            console.print(f"   • [cyan]GET  /health[/cyan] - Health check")
            console.print(f"   • [cyan]GET  /stats[/cyan] - Server statistics")
            console.print(f"   • [cyan]GET  /docs[/cyan] - Interactive API documentation")
            console.print(f"   • [cyan]GET  /redoc[/cyan] - Alternative API documentation")
            
            console.print(f"\n💡 [yellow]Use Ctrl+C to stop the server[/yellow]")
            console.print(f"🔧 Debug mode: [{'green' if debug else 'red'}]{'ON' if debug else 'OFF'}[/{'green' if debug else 'red'}]")
            console.print(f"📖 API Docs: [link]http://{self.host}:{self.port}/docs[/link]")
            
            # Configure logging level
            log_level = "debug" if debug else "info"
            
            # Start the server
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level=log_level,
                access_log=debug,
                reload=False  # Disable auto-reload to avoid issues
            )
            
        except OSError as e:
            if "Address already in use" in str(e):
                console.print(f"💥 [red]Port {self.port} is already in use![/red]")
                console.print(f"💡 Try using a different port: [cyan]runagent serve --port {self.port + 1}[/cyan]")
                console.print(f"💡 Or stop the existing server and try again")
            else:
                console.print(f"💥 [red]Network error: {str(e)}[/red]")
            raise
        except KeyboardInterrupt:
            console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
        except Exception as e:
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
            "server_type": "FastAPI"
        }