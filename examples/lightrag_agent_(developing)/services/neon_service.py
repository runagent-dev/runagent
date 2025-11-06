"""
Neon API Service for advanced database management
Optional service for creating databases, branches, etc.
"""

import httpx
from typing import Dict, Optional
from loguru import logger

from agent.config import LightRAGConfig


class NeonAPIService:
    """
    Optional service for Neon API operations
    Requires NEON_API_KEY and NEON_PROJECT_ID to be set
    """
    
    def __init__(self, config: LightRAGConfig):
        self.config = config
        
        if not config.neon_api_key or not config.neon_project_id:
            logger.warning("⚠️  Neon API credentials not configured")
            logger.info("   Advanced database management features will be unavailable")
            self.enabled = False
        else:
            self.enabled = True
            self.headers = {
                "Authorization": f"Bearer {config.neon_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            self.base_url = "https://console.neon.tech/api/v2"
    
    async def get_project_info(self) -> Optional[Dict]:
        """Get project information"""
        if not self.enabled:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/projects/{self.config.neon_project_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ Failed to get project info: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting project info: {e}")
            return None
    
    async def list_databases(self, branch_id: Optional[str] = None) -> list:
        """List databases in a branch"""
        if not self.enabled:
            return []
        
        try:
            # If no branch_id, get default branch
            if not branch_id:
                project = await self.get_project_info()
                if not project:
                    return []
                
                branches = project.get("project", {}).get("branches", [])
                for branch in branches:
                    if branch.get("primary") or branch.get("name") == "main":
                        branch_id = branch["id"]
                        break
            
            if not branch_id:
                return []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/projects/{self.config.neon_project_id}/branches/{branch_id}/databases",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("databases", [])
                
                return []
                
        except Exception as e:
            logger.error(f"❌ Error listing databases: {e}")
            return []
    
    async def create_database(
        self,
        database_name: str,
        owner_name: str = "neondb_owner",
        branch_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Create a new database"""
        if not self.enabled:
            logger.warning("⚠️  Cannot create database: Neon API not configured")
            return None
        
        try:
            # If no branch_id, get default branch
            if not branch_id:
                project = await self.get_project_info()
                if not project:
                    return None
                
                branches = project.get("project", {}).get("branches", [])
                for branch in branches:
                    if branch.get("primary") or branch.get("name") == "main":
                        branch_id = branch["id"]
                        break
            
            if not branch_id:
                return None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/projects/{self.config.neon_project_id}/branches/{branch_id}/databases",
                    headers=self.headers,
                    json={
                        "database": {
                            "name": database_name,
                            "owner_name": owner_name
                        }
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Created database: {database_name}")
                    return response.json()
                elif response.status_code == 409:
                    logger.info(f"ℹ️  Database already exists: {database_name}")
                    return {"database": {"name": database_name}}
                else:
                    logger.error(f"❌ Failed to create database: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error creating database: {e}")
            return None
    
    async def get_connection_string(
        self,
        database_name: str,
        branch_id: Optional[str] = None,
        pooled: bool = True
    ) -> Optional[str]:
        """Get connection string for a database"""
        if not self.enabled:
            return None
        
        try:
            # If no branch_id, get default branch
            if not branch_id:
                project = await self.get_project_info()
                if not project:
                    return None
                
                branches = project.get("project", {}).get("branches", [])
                for branch in branches:
                    if branch.get("primary") or branch.get("name") == "main":
                        branch_id = branch["id"]
                        break
            
            if not branch_id:
                return None
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/projects/{self.config.neon_project_id}/connection_uri",
                    headers=self.headers,
                    params={
                        "database_name": database_name,
                        "branch_id": branch_id,
                        "role_name": "neondb_owner",
                        "pooled": str(pooled).lower()
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("uri")
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting connection string: {e}")
            return None