import os
import socket
from typing import Tuple
from rich.console import Console

console = Console()


class PortManager:
    """Utility class for managing port allocation"""
    
    DEFAULT_START_PORT = 8450
    DEFAULT_HOST = "127.0.0.1"
    MAX_PORT_ATTEMPTS = 5
    
    @staticmethod
    def is_port_available(host: str, port: int) -> bool:
        """Check if a port is available on the given host"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection fails
        except Exception:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return False
    
    @staticmethod
    def find_available_port(host: str = DEFAULT_HOST, start_port: int = DEFAULT_START_PORT) -> int:
        """Find the next available port starting from start_port"""
        for port in range(start_port, start_port + PortManager.MAX_PORT_ATTEMPTS):
            if PortManager.is_port_available(host, port):
                return port
        
        raise RuntimeError(f"No available ports found in range {start_port}-{start_port + PortManager.MAX_PORT_ATTEMPTS}")
    
    @staticmethod
    def allocate_unique_address(used_ports: list = None) -> Tuple[str, int]:
        """Allocate a unique host:port combination"""
        host = PortManager.DEFAULT_HOST
        used_ports = used_ports or []
        
        # Start from default port and find the first available
        start_port = PortManager.DEFAULT_START_PORT
        
        for port in range(start_port, start_port + PortManager.MAX_PORT_ATTEMPTS):
            if port not in used_ports and PortManager.is_port_available(host, port):
                console.print(f"🔌 Allocated address: [blue]{host}:{port}[/blue]")
                return host, port
        
        raise RuntimeError("No available ports found for allocation")
    
    @staticmethod
    def get_used_ports_from_db(db_service) -> list:
        """Get list of ports currently used by agents in the database"""
        try:
            agents = db_service.list_agents()
            used_ports = []
            
            for agent in agents:
                if agent.get('port'):
                    used_ports.append(agent['port'])
            
            return used_ports
        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            console.print(f"[yellow]Warning: Could not fetch used ports: {e}[/yellow]")
            return []