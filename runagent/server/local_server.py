# runagent/server/local_server.py
import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
from pathlib import Path
from rich.console import Console

console = Console()

class LocalServer:
    """Local server for testing deployed agents"""
    
    def __init__(self, port: int = 8450, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.deployments_dir = Path("deployments")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "server": "RunAgent Local Server",
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time(),
                "version": "1.0.0"
            })
        
        @self.app.route('/agents', methods=['GET'])
        def list_agents():
            """List all deployed agents"""
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                agents_result = local_client.list_local_agents()
                
                if agents_result.get('success'):
                    agents = agents_result.get('agents', [])
                    return jsonify({
                        "success": True,
                        "agents": agents,
                        "total": len(agents)
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to list agents",
                        "agents": []
                    })
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "agents": []
                }), 500
        
        @self.app.route('/agents/<agent_id>', methods=['GET'])
        def get_agent_info(agent_id):
            """Get detailed agent information"""
            try:
                from runagent.client.local_client import LocalClient
                
                local_client = LocalClient()
                agent_info = local_client.get_agent_info(agent_id)
                
                if agent_info.get('success'):
                    return jsonify({
                        "success": True,
                        "agent_info": agent_info.get('agent_info')
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": agent_info.get('error')
                    }), 404
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500
        
        @self.app.route('/agents/<agent_id>', methods=['DELETE'])
        def delete_agent(agent_id):
            """Delete a deployed agent"""
            try:
                agent_dir = self.deployments_dir / agent_id
                
                if not agent_dir.exists():
                    return jsonify({
                        "success": False,
                        "error": f"Agent {agent_id} not found"
                    }), 404
                
                # Remove agent directory
                import shutil
                shutil.rmtree(agent_dir)
                
                # Remove deployment info
                deployments_info_dir = Path.cwd() / ".deployments"
                info_file = deployments_info_dir / f"{agent_id}.json"
                if info_file.exists():
                    info_file.unlink()
                
                console.print(f"🗑️ Deleted agent: [red]{agent_id}[/red]")
                
                return jsonify({
                    "success": True,
                    "message": f"Agent {agent_id} deleted successfully"
                })
                
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Failed to delete agent: {str(e)}"
                }), 500
        
        @self.app.errorhandler(404)
        def not_found(error):
            """Handle 404 errors"""
            return jsonify({
                "success": False,
                "error": "Endpoint not found",
                "available_endpoints": {
                    "GET /": "List available agents",
                    "GET /agents": "List all agents",
                    "GET /agents/<id>": "Get agent info",
                    "POST /agents/<id>/run": "Run agent",
                    "GET /agents/<id>/status": "Get agent status",
                    "DELETE /agents/<id>": "Delete agent",
                    "GET /health": "Health check"
                }
            }), 404
        
        @self.app.errorhandler(405)
        def method_not_allowed(error):
            """Handle 405 errors"""
            return jsonify({
                "success": False,
                "error": "Method not allowed for this endpoint"
            }), 405
        
        @self.app.errorhandler(500)
        def internal_error(error):
            """Handle 500 errors"""
            console.print(f"💥 [red]Internal server error: {str(error)}[/red]")
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500
        
        # Add CORS support for development
        @self.app.after_request
        def after_request(response):
            """Add CORS headers"""
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            return response
        
        # Handle preflight requests
        @self.app.route('/<path:path>', methods=['OPTIONS'])
        @self.app.route('/agents/<agent_id>/run', methods=['OPTIONS'])
        def handle_options(path=None, agent_id=None):
            """Handle preflight OPTIONS requests"""
            return jsonify({"success": True}), 200
    
    def start(self, debug: bool = False):
        """Start the local server"""
        try:
            # Ensure deployments directory exists
            self.deployments_dir.mkdir(exist_ok=True)
            
            console.print(f"🚀 Starting RunAgent Local Server...")
            console.print(f"🌐 Server URL: [bold blue]http://{self.host}:{self.port}[/bold blue]")
            console.print(f"📁 Deployments directory: [blue]{self.deployments_dir.absolute()}[/blue]")
            
            # Check for existing agents
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                agents_result = local_client.list_local_agents()
                
                if agents_result.get('success'):
                    agent_count = len(agents_result.get('agents', []))
                    if agent_count > 0:
                        console.print(f"📊 Found {agent_count} deployed agent(s)")
                    else:
                        console.print("📊 No agents currently deployed")
            except:
                console.print("📊 Could not check existing agents")
            
            console.print(f"\n📋 Available endpoints:")
            console.print(f"   • [cyan]GET  /[/cyan] - List agents overview")
            console.print(f"   • [cyan]GET  /agents[/cyan] - List all agents")
            console.print(f"   • [cyan]GET  /agents/<id>[/cyan] - Get agent info")
            console.print(f"   • [cyan]POST /agents/<id>/run[/cyan] - Run agent")
            console.print(f"   • [cyan]GET  /agents/<id>/status[/cyan] - Agent status")
            console.print(f"   • [cyan]DELETE /agents/<id>[/cyan] - Delete agent")
            console.print(f"   • [cyan]GET  /health[/cyan] - Health check")
            
            console.print(f"\n💡 [yellow]Use Ctrl+C to stop the server[/yellow]")
            console.print(f"🔧 Debug mode: [{'green' if debug else 'red'}]{'ON' if debug else 'OFF'}[/{'green' if debug else 'red'}]")
            
            # Disable Flask's default startup message in production
            import logging
            if not debug:
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.ERROR)
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=debug,
                threaded=True,
                use_reloader=False  # Disable reloader to avoid issues
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
    
    def stop(self):
        """Stop the server gracefully"""
        console.print("🛑 Stopping server...")
        # Flask doesn't have a built-in stop method, but this can be used for cleanup
        pass
    
    def get_server_info(self) -> dict:
        """Get server information"""
        return {
            "host": self.host,
            "port": self.port,
            "deployments_dir": str(self.deployments_dir.absolute()),
            "url": f"http://{self.host}:{self.port}",
            "status": "running"
        }.route('/', methods=['GET'])
        def home():
            """Root endpoint showing available agents"""
            try:
                from runagent.client.local_client import LocalClient
                local_client = LocalClient()
                agents_result = local_client.list_local_agents()
                
                if agents_result.get('success'):
                    agents = agents_result.get('agents', [])
                    agent_endpoints = {}
                    
                    for agent in agents:
                        agent_id = agent.get('agent_id')
                        if agent_id:
                            agent_endpoints[agent_id] = {
                                "endpoint": f"/agents/{agent_id}/run",
                                "deployed_at": agent.get('deployed_at'),
                                "framework": agent.get('framework', 'unknown')
                            }
                    
                    return jsonify({
                        "message": "RunAgent Local Server",
                        "available_agents": agent_endpoints,
                        "server_info": {
                            "host": self.host,
                            "port": self.port,
                            "total_agents": len(agents)
                        },
                        "endpoints": {
                            "GET /": "List available agents",
                            "POST /agents/:agent_id/run": "Run an agent",
                            "GET /agents/:agent_id/status": "Get agent status"
                        }
                    })
                else:
                    return jsonify({
                        "message": "RunAgent Local Server",
                        "error": "Failed to list agents",
                        "available_agents": {}
                    })
                    
            except Exception as e:
                return jsonify({
                    "message": "RunAgent Local Server",
                    "error": str(e),
                    "available_agents": {}
                })
        
        @self.app.route('/agents/<agent_id>/run', methods=['POST'])
        def run_agent(agent_id):
            """Run a deployed agent"""
            try:
                from runagent.client.local_client import LocalClient
                
                console.print(f"🚀 Running agent: [cyan]{agent_id}[/cyan]")
                
                # Get input data
                input_data = request.get_json() or {}
                
                # Log the request
                console.print(f"📥 Input: {json.dumps(input_data, indent=2)[:200]}...")
                
                # Initialize local client and run agent
                local_client = LocalClient()
                result = local_client.run_agent(agent_id, input_data)
                
                # Log the response
                if result.get('success'):
                    console.print(f"✅ Agent [cyan]{agent_id}[/cyan] completed successfully")
                else:
                    console.print(f"❌ Agent [cyan]{agent_id}[/cyan] failed: {result.get('error')}")
                
                return jsonify(result)
                
            except Exception as e:
                error_msg = f"Server error running agent {agent_id}: {str(e)}"
                console.print(f"💥 [red]{error_msg}[/red]")
                
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 500
        
        @self.app.route('/agents/<agent_id>/status', methods=['GET'])
        def get_agent_status(agent_id):
            """Get agent status"""
            try:
                from runagent.client.local_client import LocalClient
                
                local_client = LocalClient()
                agent_info = local_client.get_agent_info(agent_id)
                
                if agent_info.get('success'):
                    metadata = agent_info.get('agent_info', {})
                    
                    return jsonify({
                        "success": True,
                        "agent_id": agent_id,
                        "status": "deployed",
                        "deployed_at": metadata.get('deployed_at'),
                        "framework": metadata.get('framework'),
                        "local": True,
                        "endpoint": f"http://{self.host}:{self.port}/agents/{agent_id}/run"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": agent_info.get('error')
                    }), 404
                    
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Status check failed: {str(e)}"
                }), 500
        
        @self.app