"""
Configuration management for LightRAG Agent
Handles environment variables and settings validation
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache


class LightRAGConfig(BaseSettings):
    """LightRAG Agent Configuration"""
    
    # ============================================
    # Required: API Keys
    # ============================================
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        env="OPENAI_BASE_URL"
    )
    
    # ============================================
    # Required: Neon PostgreSQL
    # ============================================
    neon_database_url: str = Field(..., env="NEON_DATABASE_URL")
    neon_api_key: Optional[str] = Field(default=None, env="NEON_API_KEY")
    neon_project_id: Optional[str] = Field(default=None, env="NEON_PROJECT_ID")
    
    # ============================================
    # Embedding Configuration
    # ============================================
    embedding_dim: int = Field(default=1536, env="EMBEDDING_DIM")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        env="EMBEDDING_MODEL"
    )
    
    # ============================================
    # LLM Configuration
    # ============================================
    llm_model: str = Field(default="gpt-4o-mini", env="LLM_MODEL")
    vision_model: str = Field(default="gpt-4o", env="VISION_MODEL")
    
    # ============================================
    # RAG Configuration
    # ============================================
    top_k: int = Field(default=60, env="TOP_K")
    chunk_top_k: int = Field(default=20, env="CHUNK_TOP_K")
    max_entity_tokens: int = Field(default=0, env="MAX_ENTITY_TOKENS")
    max_relation_tokens: int = Field(default=0, env="MAX_RELATION_TOKENS")
    max_total_tokens: int = Field(default=30000, env="MAX_TOTAL_TOKENS")
    
    # ============================================
    # Document Processing
    # ============================================
    parser: str = Field(default="mineru", env="PARSER")
    parse_method: str = Field(default="auto", env="PARSE_METHOD")
    enable_image_processing: bool = Field(default=True, env="ENABLE_IMAGE_PROCESSING")
    enable_table_processing: bool = Field(default=True, env="ENABLE_TABLE_PROCESSING")
    enable_equation_processing: bool = Field(default=True, env="ENABLE_EQUATION_PROCESSING")
    output_dir: str = Field(default="./parsed_output", env="OUTPUT_DIR")
    
    # ============================================
    # Storage Configuration
    # ============================================
    working_dir: str = Field(default="/dev/shm/lightrag", env="WORKING_DIR")
    workspace: str = Field(default="default", env="WORKSPACE")
    
    # ============================================
    # Neo4j Configuration (for Graph Storage)
    # Must be defined BEFORE graph_storage for validation
    # ============================================
    neo4j_uri: Optional[str] = Field(default=None, env="NEO4J_URI")
    neo4j_username: Optional[str] = Field(default=None, env="NEO4J_USERNAME")
    neo4j_password: Optional[str] = Field(default=None, env="NEO4J_PASSWORD")
    neo4j_workspace: str = Field(default="base", env="NEO4J_WORKSPACE")
    
    # Storage backend selection (must be after neo4j config)
    kv_storage: str = Field(default="PGKVStorage", env="KV_STORAGE")
    vector_storage: str = Field(default="PGVectorStorage", env="VECTOR_STORAGE")
    graph_storage: str = Field(default="NetworkXStorage", env="GRAPH_STORAGE")  # NetworkX by default, use Neo4JStorage for serverless
    doc_status_storage: str = Field(default="PGDocStatusStorage", env="DOC_STATUS_STORAGE")
    
    # ============================================
    # Performance Configuration
    # ============================================
    max_parallel_insert: int = Field(default=4, env="MAX_PARALLEL_INSERT")
    llm_model_max_async: int = Field(default=4, env="LLM_MODEL_MAX_ASYNC")
    embedding_func_max_async: int = Field(default=16, env="EMBEDDING_FUNC_MAX_ASYNC")
    embedding_batch_num: int = Field(default=32, env="EMBEDDING_BATCH_NUM")
    
    # ============================================
    # Optional Configuration
    # ============================================
    enable_llm_cache: bool = Field(default=True, env="ENABLE_LLM_CACHE")
    enable_rerank: bool = Field(default=True, env="ENABLE_RERANK")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    summary_context_size: int = Field(default=10000, env="SUMMARY_CONTEXT_SIZE")
    summary_max_tokens: int = Field(default=500, env="SUMMARY_MAX_TOKENS")
    cosine_threshold: float = Field(default=0.2, env="COSINE_THRESHOLD")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"
    
    @validator("parser")
    def validate_parser(cls, v):
        """Validate parser selection"""
        valid_parsers = ["mineru", "docling"]
        if v not in valid_parsers:
            raise ValueError(f"Parser must be one of {valid_parsers}")
        return v
    
    @validator("parse_method")
    def validate_parse_method(cls, v):
        """Validate parse method"""
        valid_methods = ["auto", "ocr", "txt"]
        if v not in valid_methods:
            raise ValueError(f"Parse method must be one of {valid_methods}")
        return v
    
    @validator("neon_database_url")
    def validate_neon_url(cls, v):
        """Validate Neon database URL format"""
        if not v.startswith("postgresql://") and not v.startswith("postgres://"):
            raise ValueError("NEON_DATABASE_URL must start with postgresql:// or postgres://")
        if "sslmode" not in v:
            # Append sslmode=require if not present
            separator = "?" if "?" not in v else "&"
            v = f"{v}{separator}sslmode=require"
        return v
    
    @validator("graph_storage")
    def validate_graph_storage(cls, v, values):
        """Validate graph storage configuration"""
        if v == "Neo4JStorage":
            # Check if Neo4j credentials are provided
            neo4j_uri = values.get('neo4j_uri')
            if not neo4j_uri:
                raise ValueError(
                    "When GRAPH_STORAGE=Neo4JStorage, you must provide Neo4j configuration in .env:\n"
                    "  NEO4J_URI=neo4j://localhost:7687\n"
                    "  NEO4J_USERNAME=neo4j\n"
                    "  NEO4J_PASSWORD=your-password\n"
                    "  NEO4J_WORKSPACE=base\n\n"
                    "To use NetworkX instead (not recommended for serverless):\n"
                    "  GRAPH_STORAGE=NetworkXStorage\n\n"
                    "See NEO4J_SETUP.md for detailed setup instructions."
                )
        return v
    
    def get_postgres_config(self) -> dict:
        """Extract PostgreSQL configuration from connection string"""
        import re
        pattern = r'postgresql://([^:]+):([^@]+)@([^/]+)/([^?]+)'
        match = re.match(pattern, self.neon_database_url)
        
        if not match:
            raise ValueError("Invalid PostgreSQL connection string format")
        
        user, password, host, database = match.groups()
        
        if ':' in host:
            host, port = host.rsplit(':', 1)
        else:
            port = '5432'
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': database
        }
    
    def set_env_vars(self):
        """Set environment variables for LightRAG and dependencies"""
        # OpenAI
        os.environ['OPENAI_API_KEY'] = self.openai_api_key
        if self.openai_base_url:
            os.environ['OPENAI_BASE_URL'] = self.openai_base_url
        
        # PostgreSQL
        pg_config = self.get_postgres_config()
        os.environ['POSTGRES_USER'] = pg_config['user']
        os.environ['POSTGRES_PASSWORD'] = pg_config['password']
        os.environ['POSTGRES_HOST'] = pg_config['host']
        os.environ['POSTGRES_PORT'] = pg_config['port']
        os.environ['POSTGRES_DATABASE'] = pg_config['database']
        
        # Neo4j (if configured)
        if self.neo4j_uri:
            os.environ['NEO4J_URI'] = self.neo4j_uri
        if self.neo4j_username:
            os.environ['NEO4J_USERNAME'] = self.neo4j_username
        if self.neo4j_password:
            os.environ['NEO4J_PASSWORD'] = self.neo4j_password
        if self.neo4j_workspace:
            os.environ['NEO4J_WORKSPACE'] = self.neo4j_workspace
        
        # LightRAG specific
        os.environ['EMBEDDING_DIM'] = str(self.embedding_dim)
        os.environ['TOP_K'] = str(self.top_k)
        os.environ['CHUNK_TOP_K'] = str(self.chunk_top_k)
        os.environ['MAX_ENTITY_TOKENS'] = str(self.max_entity_tokens)
        os.environ['MAX_RELATION_TOKENS'] = str(self.max_relation_tokens)
        os.environ['MAX_TOTAL_TOKENS'] = str(self.max_total_tokens)
        os.environ['SUMMARY_CONTEXT_SIZE'] = str(self.summary_context_size)
        os.environ['SUMMARY_MAX_TOKENS'] = str(self.summary_max_tokens)
        os.environ['COSINE_THRESHOLD'] = str(self.cosine_threshold)
        os.environ['MAX_ASYNC'] = str(self.llm_model_max_async)
        
        # Document processing
        os.environ['PARSER'] = self.parser
        os.environ['PARSE_METHOD'] = self.parse_method
        os.environ['OUTPUT_DIR'] = self.output_dir


@lru_cache()
def get_config() -> LightRAGConfig:
    """Get cached configuration instance"""
    return LightRAGConfig()


def get_agent_id() -> str:
    """
    Get agent ID from environment or generate a unique one
    This is set by RunAgent when the agent is deployed
    """
    return os.environ.get('RUNAGENT_AGENT_ID', 'local-agent')