"""
Storage initialization and management for Neon PostgreSQL
Handles database setup, extension enabling, and connection management
"""

import os
import asyncpg
import asyncio
from typing import Optional
from loguru import logger

from agent.config import LightRAGConfig


class NeonStorageManager:
    """Manages Neon PostgreSQL storage initialization and health"""
    
    def __init__(self, config: LightRAGConfig):
        self.config = config
        self.connection_string = config.neon_database_url
        self._connection: Optional[asyncpg.Connection] = None
    
    async def connect(self) -> asyncpg.Connection:
        """Establish connection to Neon database"""
        if self._connection is None or self._connection.is_closed():
            try:
                self._connection = await asyncpg.connect(
                    self.connection_string,
                    ssl='require'
                )
                logger.info("✅ Connected to Neon PostgreSQL")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Neon: {e}")
                raise
        return self._connection
    
    async def close(self):
        """Close database connection"""
        if self._connection and not self._connection.is_closed():
            await self._connection.close()
            logger.info("🔌 Closed Neon PostgreSQL connection")
    
    async def initialize_database(self):
        """
        Initialize database with required extensions and tables
        This should be called once when the agent is first deployed
        """
        conn = await self.connect()
        
        try:
            # Enable vector extension for embeddings
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("✅ Enabled vector extension")
            
            # Try to enable AGE extension for graph storage (optional, only needed for PGGraphStorage)
            graph_storage = os.environ.get("GRAPH_STORAGE", self.config.workspace if hasattr(self.config, 'graph_storage') else "NetworkXStorage")
            
            if graph_storage == "PGGraphStorage":
                # AGE is required for PGGraphStorage
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS age;")
                    logger.info("✅ Enabled AGE extension for PGGraphStorage")
                    
                    await conn.execute("LOAD 'age';")
                    await conn.execute("SET search_path = ag_catalog, '$user', public;")
                    
                    graph_name = f"lightrag_{self.config.workspace}"
                    try:
                        await conn.execute(f"SELECT create_graph('{graph_name}');")
                        logger.info(f"✅ Created AGE graph: {graph_name}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            logger.info(f"ℹ️  AGE graph already exists: {graph_name}")
                        else:
                            raise
                            
                except Exception as e:
                    logger.error(f"❌ AGE extension setup failed: {e}")
                    logger.error("   CRITICAL: PGGraphStorage requires AGE extension")
                    logger.error("   Please either:")
                    logger.error("   1. Enable AGE extension in your Neon database, OR")
                    logger.error("   2. Use Neo4JStorage (recommended): Set GRAPH_STORAGE=Neo4JStorage in .env")
                    raise RuntimeError(
                        f"AGE extension is required for PGGraphStorage. "
                        f"Either enable AGE in Neon or use Neo4JStorage (GRAPH_STORAGE=Neo4JStorage)"
                    )
            else:
                # For NetworkX or Neo4j, AGE is not required
                logger.info(f"ℹ️  Graph storage: {graph_storage} (AGE extension not required)")
                
                # Try to enable AGE anyway if available (nice to have, not critical)
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS age;")
                    logger.info("✅ AGE extension available (optional)")
                except Exception:
                    logger.info("ℹ️  AGE extension not available (not required for current graph storage)")
            
            # Create metadata table for agent tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS lightrag_agents (
                    agent_id VARCHAR(255) PRIMARY KEY,
                    workspace VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    document_count INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    total_entities INTEGER DEFAULT 0,
                    total_relations INTEGER DEFAULT 0,
                    metadata JSONB,
                    UNIQUE(agent_id, workspace)
                );
            """)
            logger.info("✅ Created lightrag_agents metadata table")
            
            # Create index for faster lookups
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_lightrag_agents_workspace 
                ON lightrag_agents(workspace);
            """)
            
            logger.info("🎉 Database initialization complete!")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def register_agent(self, agent_id: str, workspace: str):
        """Register agent in metadata table"""
        conn = await self.connect()
        
        try:
            await conn.execute("""
                INSERT INTO lightrag_agents (agent_id, workspace, metadata)
                VALUES ($1, $2, $3)
                ON CONFLICT (agent_id, workspace) 
                DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """, agent_id, workspace, '{}')
            
            logger.info(f"✅ Registered agent {agent_id} in workspace {workspace}")
            
        except Exception as e:
            logger.error(f"❌ Failed to register agent: {e}")
            raise
    
    async def update_agent_stats(
        self,
        agent_id: str,
        workspace: str,
        document_count: Optional[int] = None,
        total_chunks: Optional[int] = None,
        total_entities: Optional[int] = None,
        total_relations: Optional[int] = None,
        metadata: Optional[dict] = None
    ):
        """Update agent statistics"""
        conn = await self.connect()
        
        updates = []
        values = []
        param_idx = 1
        
        if document_count is not None:
            updates.append(f"document_count = ${param_idx}")
            values.append(document_count)
            param_idx += 1
        
        if total_chunks is not None:
            updates.append(f"total_chunks = ${param_idx}")
            values.append(total_chunks)
            param_idx += 1
        
        if total_entities is not None:
            updates.append(f"total_entities = ${param_idx}")
            values.append(total_entities)
            param_idx += 1
        
        if total_relations is not None:
            updates.append(f"total_relations = ${param_idx}")
            values.append(total_relations)
            param_idx += 1
        
        if metadata is not None:
            import json
            updates.append(f"metadata = ${param_idx}")
            values.append(json.dumps(metadata))
            param_idx += 1
        
        if not updates:
            return
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.extend([agent_id, workspace])
        
        query = f"""
            UPDATE lightrag_agents 
            SET {', '.join(updates)}
            WHERE agent_id = ${param_idx} AND workspace = ${param_idx + 1}
        """
        
        try:
            await conn.execute(query, *values)
            logger.debug(f"📊 Updated stats for agent {agent_id}")
        except Exception as e:
            logger.error(f"❌ Failed to update agent stats: {e}")
    
    async def get_agent_stats(self, agent_id: str, workspace: str) -> dict:
        """Get agent statistics"""
        conn = await self.connect()
        
        try:
            row = await conn.fetchrow("""
                SELECT * FROM lightrag_agents 
                WHERE agent_id = $1 AND workspace = $2
            """, agent_id, workspace)
            
            if row:
                import json
                return {
                    'agent_id': row['agent_id'],
                    'workspace': row['workspace'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'document_count': row['document_count'],
                    'total_chunks': row['total_chunks'],
                    'total_entities': row['total_entities'],
                    'total_relations': row['total_relations'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get agent stats: {e}")
            return None
    
    async def health_check(self) -> dict:
        """Check database health and connectivity"""
        try:
            conn = await self.connect()
            
            # Check basic connectivity
            await conn.execute("SELECT 1")
            
            # Check extensions
            vector_enabled = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """)
            
            age_enabled = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'age'
                )
            """)
            
            # Check AGE graph exists
            age_graph_exists = False
            if age_enabled:
                try:
                    graph_name = f"lightrag_{self.config.workspace}"
                    await conn.execute("LOAD 'age';")
                    await conn.execute("SET search_path = ag_catalog, '$user', public;")
                    
                    result = await conn.fetchval(f"""
                        SELECT EXISTS(
                            SELECT 1 FROM ag_catalog.ag_graph WHERE name = '{graph_name}'
                        )
                    """)
                    age_graph_exists = bool(result)
                except Exception:
                    pass
            
            # Check tables
            tables = await conn.fetch("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE 'lightrag%'
            """)
            
            # Check Neo4j if configured
            neo4j_health = None
            graph_storage = os.environ.get("GRAPH_STORAGE", getattr(self.config, "graph_storage", "NetworkXStorage"))
            if graph_storage == "Neo4JStorage":
                try:
                    from services.neo4j_validator import validate_neo4j_connection
                    neo4j_uri = os.environ.get("NEO4J_URI")
                    neo4j_user = os.environ.get("NEO4J_USERNAME")
                    neo4j_pass = os.environ.get("NEO4J_PASSWORD")
                    neo4j_workspace = os.environ.get("NEO4J_WORKSPACE", "base")
                    
                    if neo4j_uri and neo4j_user and neo4j_pass:
                        neo4j_result = await validate_neo4j_connection(
                            neo4j_uri, neo4j_user, neo4j_pass, neo4j_workspace
                        )
                        neo4j_health = neo4j_result.get("health")
                except Exception as e:
                    logger.warning(f"⚠️  Neo4j health check skipped: {e}")
                    neo4j_health = {"status": "not_configured", "note": "Neo4j check skipped"}
            
            return {
                'status': 'healthy',
                'connected': True,
                'extensions': {
                    'vector': vector_enabled,
                    'age': age_enabled,
                    'age_graph_ready': age_graph_exists
                },
                'tables': [row['tablename'] for row in tables],
                'database': self.config.get_postgres_config()['database'],
                'neo4j': neo4j_health,
                'serverless_ready': vector_enabled and (age_graph_exists or neo4j_health is not None)
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }
    
    async def cleanup_agent_data(self, agent_id: str, workspace: str):
        """Clean up agent data (for testing/reset)"""
        conn = await self.connect()
        
        try:
            # Delete from metadata table
            await conn.execute("""
                DELETE FROM lightrag_agents 
                WHERE agent_id = $1 AND workspace = $2
            """, agent_id, workspace)
            
            logger.info(f"🧹 Cleaned up data for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup agent data: {e}")
            raise


async def initialize_neon_storage(config: LightRAGConfig) -> NeonStorageManager:
    """
    Initialize Neon storage for LightRAG
    This is the main entry point for storage setup
    """
    manager = NeonStorageManager(config)
    
    # Initialize database
    await manager.initialize_database()
    
    # Run health check
    health = await manager.health_check()
    logger.info(f"🏥 Database health: {health}")
    
    return manager