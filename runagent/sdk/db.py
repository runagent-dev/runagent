import json
import os
import uuid
import typing as t
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    desc,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

from runagent.constants import LOCAL_CACHE_DIRECTORY, DATABASE_FILE_NAME
from runagent.utils.port import PortManager


console = Console()


Base = declarative_base()


class Agent(Base):
    """Agent model - Enhanced with config-based fields"""

    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True)
    agent_path = Column(String, nullable=False)
    host = Column(String, nullable=False, default="localhost")
    port = Column(Integer, nullable=False, default=8000)
    framework = Column(String)
    status = Column(String, default="initialized")  # Local deployment status
    remote_status = Column(String, default="initialized")  # Remote deployment status
    is_local = Column(Boolean, default=True)  # True for local agents, False for remote uploads
    fingerprint = Column(String, nullable=True)  # Agent folder fingerprint for duplicate detection
    deployed_at = Column(DateTime, nullable=True)  # Made nullable since agents start as 'initialized'
    last_run = Column(DateTime)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    
    # NEW FIELDS - Config-based agent information
    agent_name = Column(String, nullable=True)  # From runagent.config.json
    description = Column(Text, nullable=True)   # From runagent.config.json
    template = Column(String, nullable=True)    # From runagent.config.json
    version = Column(String, nullable=True)     # From runagent.config.json
    initialized_at = Column(DateTime, nullable=True)  # When agent was first initialized
    config_fingerprint = Column(String, nullable=True)  # Hash of config file for change detection
    project_id = Column(String, nullable=True)  # Project/organization identifier

    # Relationships
    runs = relationship(
        "AgentRun", back_populates="agent", cascade="all, delete-orphan"
    )
    invocations = relationship(
        "AgentInvocation", back_populates="agent", cascade="all, delete-orphan"
    )
    agent_logs = relationship(
        "AgentLog", back_populates="agent", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_agents_status", "status"),)


class AgentRun(Base):
    """Agent run model - UNCHANGED to maintain compatibility"""

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(
        String, ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False
    )
    input_data = Column(Text, nullable=False)
    output_data = Column(Text)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    execution_time = Column(Float)
    started_at = Column(DateTime, default=func.current_timestamp())
    completed_at = Column(DateTime)

    # Relationship
    agent = relationship("Agent", back_populates="runs")

    # Indexes
    __table_args__ = (
        Index("idx_agent_runs_agent_id", "agent_id"),
        Index("idx_agent_runs_started_at", "started_at"),
    )


class AgentInvocation(Base):
    """NEW: Agent invocation tracking table"""

    __tablename__ = "agent_invocations"

    # Primary fields
    invocation_id = Column(String, primary_key=True)  # UUID for each invocation
    agent_id = Column(
        String, ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False
    )
    
    # Input/Output tracking
    input_data = Column(Text, nullable=False)  # JSON serialized input
    output_data = Column(Text, nullable=True)  # JSON serialized output
    error_detail = Column(Text, nullable=True)  # Error details if failed
    
    # Timing tracking
    request_timestamp = Column(DateTime, nullable=False, default=func.current_timestamp())
    response_timestamp = Column(DateTime, nullable=True)
    execution_time_ms = Column(Float, nullable=True)  # Execution time in milliseconds
    
    # Status tracking
    status = Column(String, nullable=False, default="pending")  # pending, completed, failed
    
    # Additional metadata
    entrypoint_tag = Column(String, nullable=True)  # Which entrypoint was called
    sdk_type = Column(String, nullable=True)  # cli, python-sdk, etc.
    client_info = Column(Text, nullable=True)  # JSON with client details
    
    # Relationship
    agent = relationship("Agent", back_populates="invocations")

    # Indexes for performance
    __table_args__ = (
        Index("idx_invocations_agent_id", "agent_id"),
        Index("idx_invocations_request_timestamp", "request_timestamp"),
        Index("idx_invocations_status", "status"),
        Index("idx_invocations_agent_status", "agent_id", "status"),  # Composite index
    )


class AgentLog(Base):
    """Agent log model for storing detailed logs"""

    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(
        String, ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False
    )
    log_level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    execution_id = Column(String, nullable=True)

    # Relationship
    agent = relationship("Agent", back_populates="agent_logs")

    # Indexes
    __table_args__ = (
        Index("idx_agent_logs_agent_id", "agent_id"),
        Index("idx_agent_logs_created_at", "created_at"),
        Index("idx_agent_logs_level", "log_level"),
    )


class UserMetadata(Base):
    """User metadata model for storing user configuration as key-value pairs"""

    __tablename__ = "user_metadata"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)  # Store JSON-serialized values
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # Indexes
    __table_args__ = (Index("idx_user_metadata_key", "key"),)

class DBManager:
    """Low-level database manager for SQLAlchemy operations"""

    def __init__(self, db_path: Path = None):
        """
        Initialize the database manager

        Args:
            db_path: Path to the SQLite database file
        """
        if db_path is None:
            db_path = Path(LOCAL_CACHE_DIRECTORY) / DATABASE_FILE_NAME

        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None

        db_existed = db_path.exists()
        self._init_database()

        if not db_existed:
            console.print("✅ Database initialized successfully")

    def _init_database(self):
        """Initialize the database with SQLAlchemy"""
        if not self.db_path.exists():
            console.print(f"🗃️ Initializing database: [blue]{self.db_path}[/blue]")

        try:
            # Create database engine
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,  # Set to True for SQL debugging
                connect_args={"check_same_thread": False},
            )

            # Create session factory
            self.SessionLocal = sessionmaker(bind=self.engine)

            # Create all tables
            Base.metadata.create_all(bind=self.engine)

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            console.print(f"[red]Error initializing database: {e}[/red]")
            raise

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    def ensure_initialized(self):
        """Ensure database is initialized"""
        if not self.db_path.exists():
            self._init_database()
        elif not self.is_initialized():
            self._init_database()

    def is_initialized(self) -> bool:
        """Check if database is properly initialized"""
        if not self.db_path.exists():
            return False

        try:
            # Check if we can connect and tables exist
            with self.get_session() as session:
                session.execute("SELECT 1 FROM agents LIMIT 1")
                session.execute("SELECT 1 FROM agent_runs LIMIT 1")
            return True
        except Exception:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            return False

    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DBService:
    """High-level database service with business logic and RestClient integration"""

    def __init__(self, db_path: Path = None, rest_client=None):
        """
        Initialize the database service

        Args:
            db_path: Path to the SQLite database file
            rest_client: RestClient instance for API limit checks
        """
        self.db_manager = DBManager(db_path)
        self.rest_client = rest_client

    def start_invocation(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        entrypoint_tag: str = None,
        sdk_type: str = "unknown",
        client_info: Dict[str, Any] = None
    ) -> str:
        """
        Start a new agent invocation and return invocation_id
        
        Args:
            agent_id: ID of the agent being invoked
            input_data: Input data for the invocation
            entrypoint_tag: Which entrypoint is being called
            sdk_type: Type of SDK (cli, python-sdk, etc.)
            client_info: Additional client information
            
        Returns:
            invocation_id: Unique ID for this invocation
        """
        with self.db_manager.get_session() as session:
            try:
                # Generate unique invocation ID
                invocation_id = str(uuid.uuid4())
                
                # Create invocation record
                invocation = AgentInvocation(
                    invocation_id=invocation_id,
                    agent_id=agent_id,
                    input_data=json.dumps(input_data),
                    entrypoint_tag=entrypoint_tag,
                    sdk_type=sdk_type,
                    client_info=json.dumps(client_info) if client_info else None,
                    status="pending"
                )
                
                session.add(invocation)
                session.commit()
                
                console.print(f"🚀 [cyan]Started invocation: Invocation ID = {invocation_id}[/cyan]")
                return invocation_id
                
            except Exception as e:
                session.rollback()
                console.print(f"❌ [red]Failed to start invocation: {e}[/red]")
                raise

    def complete_invocation(
        self,
        invocation_id: str,
        output_data: Any = None,
        error_detail: str = None,
        execution_time_ms: float = None
    ) -> bool:
        """
        Complete an agent invocation with results
        
        Args:
            invocation_id: ID of the invocation to complete
            output_data: Output data from the invocation (if successful)
            error_detail: Error details (if failed)
            execution_time_ms: Execution time in milliseconds
            
        Returns:
            bool: True if update successful
        """
        with self.db_manager.get_session() as session:
            try:
                # Find the invocation
                invocation = session.query(AgentInvocation).filter(
                    AgentInvocation.invocation_id == invocation_id
                ).first()
                
                if not invocation:
                    console.print(f"⚠️ [yellow]Invocation {invocation_id} not found[/yellow]")
                    return False
                
                # Update invocation with results
                invocation.response_timestamp = func.current_timestamp()
                invocation.execution_time_ms = execution_time_ms
                
                if error_detail:
                    invocation.status = "failed"
                    invocation.error_detail = error_detail
                    console.print(f"❌ [red]Completed invocation {invocation_id[:8]}... with error[/red]")
                else:
                    invocation.status = "completed"
                    invocation.output_data = json.dumps(output_data) if output_data else None
                    console.print(f"✅ [green]Completed invocation {invocation_id[:8]}... successfully[/green]")
                
                session.commit()
                return True
                
            except Exception as e:
                session.rollback()
                console.print(f"❌ [red]Failed to complete invocation: {e}[/red]")
                return False

    def get_invocation(self, invocation_id: str) -> Optional[Dict]:
        """Get invocation details by ID"""
        with self.db_manager.get_session() as session:
            try:
                invocation = session.query(AgentInvocation).filter(
                    AgentInvocation.invocation_id == invocation_id
                ).first()
                
                if not invocation:
                    return None
                
                return {
                    "invocation_id": invocation.invocation_id,
                    "agent_id": invocation.agent_id,
                    "input_data": json.loads(invocation.input_data) if invocation.input_data else None,
                    "output_data": json.loads(invocation.output_data) if invocation.output_data else None,
                    "error_detail": invocation.error_detail,
                    "request_timestamp": invocation.request_timestamp.isoformat() if invocation.request_timestamp else None,
                    "response_timestamp": invocation.response_timestamp.isoformat() if invocation.response_timestamp else None,
                    "execution_time_ms": invocation.execution_time_ms,
                    "status": invocation.status,
                    "entrypoint_tag": invocation.entrypoint_tag,
                    "sdk_type": invocation.sdk_type,
                    "client_info": json.loads(invocation.client_info) if invocation.client_info else None,
                }
                
            except Exception as e:
                console.print(f"Error getting invocation: {e}")
                return None

    def list_invocations(
        self, 
        agent_id: str = None, 
        status: str = None, 
        limit: int = 50,
        order_by: str = "request_timestamp"
    ) -> List[Dict]:
        """List invocations with optional filtering"""
        with self.db_manager.get_session() as session:
            try:
                query = session.query(AgentInvocation)
                
                # Apply filters
                if agent_id:
                    query = query.filter(AgentInvocation.agent_id == agent_id)
                if status:
                    query = query.filter(AgentInvocation.status == status)
                
                # Apply ordering
                if order_by == "request_timestamp":
                    query = query.order_by(desc(AgentInvocation.request_timestamp))
                elif order_by == "response_timestamp":
                    query = query.order_by(desc(AgentInvocation.response_timestamp))
                
                # Apply limit
                invocations = query.limit(limit).all()
                
                return [
                    {
                        "invocation_id": inv.invocation_id,
                        "agent_id": inv.agent_id,
                        "input_data": json.loads(inv.input_data) if inv.input_data else None,
                        "output_data": json.loads(inv.output_data) if inv.output_data else None,
                        "error_detail": inv.error_detail,
                        "request_timestamp": inv.request_timestamp.isoformat() if inv.request_timestamp else None,
                        "response_timestamp": inv.response_timestamp.isoformat() if inv.response_timestamp else None,
                        "execution_time_ms": inv.execution_time_ms,
                        "status": inv.status,
                        "entrypoint_tag": inv.entrypoint_tag,
                        "sdk_type": inv.sdk_type,
                        "client_info": json.loads(inv.client_info) if inv.client_info else None,
                    }
                    for inv in invocations
                ]
                
            except Exception as e:
                console.print(f"Error listing invocations: {e}")
                return []

    def get_invocation_stats(self, agent_id: str = None) -> Dict:
        """Get invocation statistics"""
        with self.db_manager.get_session() as session:
            try:
                query = session.query(AgentInvocation)
                if agent_id:
                    query = query.filter(AgentInvocation.agent_id == agent_id)
                
                # Basic counts
                total_invocations = query.count()
                completed_invocations = query.filter(AgentInvocation.status == "completed").count()
                failed_invocations = query.filter(AgentInvocation.status == "failed").count()
                pending_invocations = query.filter(AgentInvocation.status == "pending").count()
                
                # Calculate success rate
                success_rate = (completed_invocations / total_invocations * 100) if total_invocations > 0 else 0
                
                # Average execution time
                avg_execution_time = None
                if completed_invocations > 0:
                    avg_result = session.query(func.avg(AgentInvocation.execution_time_ms)).filter(
                        AgentInvocation.status == "completed"
                    )
                    if agent_id:
                        avg_result = avg_result.filter(AgentInvocation.agent_id == agent_id)
                    avg_execution_time = avg_result.scalar()
                
                return {
                    "total_invocations": total_invocations,
                    "completed_invocations": completed_invocations,
                    "failed_invocations": failed_invocations,
                    "pending_invocations": pending_invocations,
                    "success_rate": round(success_rate, 2),
                    "avg_execution_time_ms": round(avg_execution_time, 2) if avg_execution_time else None,
                    "agent_id": agent_id,
                }
                
            except Exception as e:
                console.print(f"Error getting invocation stats: {e}")
                return {}

    def cleanup_old_invocations(self, days_old: int = 30) -> int:
        """Clean up old invocation records"""
        with self.db_manager.get_session() as session:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                deleted_count = (
                    session.query(AgentInvocation)
                    .filter(AgentInvocation.request_timestamp < cutoff_date)
                    .delete()
                )
                session.commit()
                console.print(f"🧹 [green]Cleaned up {deleted_count} old invocations[/green]")
                return deleted_count
            except Exception as e:
                session.rollback()
                console.print(f"Error cleaning up old invocations: {e}")
                return 0
        

    def add_agent(
        self,
        agent_id: str,
        agent_path: str,
        host: str = "localhost",
        port: int = 8450,
        framework: str = None,
        status: str = "deployed",
        agent_name: str = None,
        description: str = None,
        template: str = None,
        version: str = None,
        initialized_at: str = None,
        config_fingerprint: str = None,
        project_id: str = None,
    ) -> Dict:
        if hasattr(framework, 'value'):
            framework = framework.value
        elif framework is not None:
            framework = str(framework)
        """
        Add a new agent with smart limit enforcement

        Args:
            agent_id: Unique agent identifier
            agent_path: Path to agent directory
            host: Host address
            port: Port number
            framework: Framework type (langchain, langgraph, etc.)

        Returns:
            Dictionary with success status and details
        """
        if not agent_id or not agent_path:
            return {
                "success": False,
                "error": "Missing required fields",
                "code": "INVALID_INPUT",
            }

        with self.db_manager.get_session() as session:
            try:
                # Check if agent already exists
                existing_agent = (
                    session.query(Agent).filter(Agent.agent_id == agent_id).first()
                )
                if existing_agent:
                    return {
                        "success": False,
                        "error": f"Agent {agent_id} already exists",
                        "code": "AGENT_EXISTS",
                    }

                new_agent = Agent(
                    agent_id=agent_id,
                    agent_path=str(agent_path),
                    host=host,
                    port=port,
                    framework=framework,
                    status=status,
                    remote_status="initialized",  # Default remote status
                    agent_name=agent_name,
                    description=description,
                    template=template,
                    version=version,
                    initialized_at=initialized_at,
                    config_fingerprint=config_fingerprint,
                    project_id=project_id,
                )

                session.add(new_agent)
                session.commit()

                return {
                    "success": True,
                    "message": f"Agent {agent_id} added successfully",
                }

            except Exception as e:
                session.rollback()
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "code": "DATABASE_ERROR",
                }

    def replace_agent(
        self,
        old_agent_id: str,
        new_agent_id: str,
        agent_path: str,
        host: str = "localhost",
        port: int = 8000,
        framework: str = None,
    ) -> Dict:
        """
        DEPRECATED: Agent IDs are immutable and cannot be replaced.
        This method is disabled to maintain data integrity.
        
        Agent IDs are UUIDs generated at creation time and should never be modified.
        To use a different agent, create a new agent with 'runagent init' or 'runagent serve'.

        Args:
            old_agent_id: Agent ID to replace (deprecated)
            new_agent_id: New agent ID (deprecated)
            agent_path: Path to agent directory (deprecated)
            host: Host address (deprecated)
            port: Port number (deprecated)
            framework: Framework type (deprecated)

        Returns:
            Dictionary with error indicating this operation is not allowed
        """
        return {
            "success": False,
            "error": "Agent ID replacement is not allowed. Agent IDs are immutable UUIDs generated at creation time.",
            "code": "IMMUTABLE_AGENT_ID",
            "message": "To use a different agent, create a new agent with 'runagent init' or 'runagent serve'."
        }

    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete agent from database - DISABLED for this implementation

        Args:
            agent_id: Agent identifier

        Returns:
            Always False since deletion is not allowed
        """
        console.print(
            f"⚠️ Agent deletion is disabled. Agent {agent_id} cannot be deleted from database."
        )
        console.print(f"💡 Each agent has a unique immutable ID. Create a new agent with 'runagent init' or 'runagent serve'.")
        return False

    def update_api_key(self, api_key: str) -> Dict:
        """
        Update API key and refresh limits (deprecated - use RestClient directly)

        Args:
            api_key: New API key

        Returns:
            Dictionary with validation results
        """
        console.print(
            "[yellow]⚠️ update_api_key is deprecated. Please configure API key in RestClient.[/yellow]"
        )
        return {
            "success": False,
            "error": "API key management moved to RestClient. Please use RestClient for API operations.",
            "deprecated": True,
        }

    def clear_api_key(self) -> Dict:
        """Clear API key and revert to default limits (deprecated)"""
        console.print(
            "[yellow]⚠️ clear_api_key is deprecated. Please configure API key in RestClient.[/yellow]"
        )
        return {
            "success": False,
            "error": "API key management moved to RestClient. Please use RestClient for API operations.",
            "deprecated": True,
        }

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent information from database"""
        with self.db_manager.get_session() as session:
            try:
                agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                if not agent:
                    return None

                return {
                    "agent_id": agent.agent_id,
                    "agent_path": agent.agent_path,
                    "host": agent.host,
                    "port": agent.port,
                    "framework": agent.framework,
                    "status": agent.status,
                    "deployed_at": (
                        agent.deployed_at.isoformat() if agent.deployed_at else None
                    ),
                    "last_run": agent.last_run.isoformat() if agent.last_run else None,
                    "run_count": agent.run_count,
                    "success_count": agent.success_count,
                    "error_count": agent.error_count,
                    "created_at": (
                        agent.created_at.isoformat() if agent.created_at else None
                    ),
                    "updated_at": (
                        agent.updated_at.isoformat() if agent.updated_at else None
                    ),
                }
            except Exception as e:
                console.print(f"Error getting agent from database: {e}")
                return None

    def get_agent_by_path(self, agent_path: str) -> Optional[Dict]:
        """Get agent information by agent path"""
        with self.db_manager.get_session() as session:
            try:
                # Normalize path for comparison
                normalized_path = str(Path(agent_path).resolve())
                
                agent = session.query(Agent).filter(
                    Agent.agent_path == normalized_path
                ).first()
                
                if not agent:
                    return None

                return {
                    "agent_id": agent.agent_id,
                    "agent_path": agent.agent_path,
                    "host": agent.host,
                    "port": agent.port,
                    "framework": agent.framework,
                    "status": agent.status,
                    "is_local": agent.is_local,
                    "fingerprint": agent.fingerprint,
                    "deployed_at": (
                        agent.deployed_at.isoformat() if agent.deployed_at else None
                    ),
                    "last_run": agent.last_run.isoformat() if agent.last_run else None,
                    "run_count": agent.run_count,
                    "success_count": agent.success_count,
                    "error_count": agent.error_count,
                    "created_at": (
                        agent.created_at.isoformat() if agent.created_at else None
                    ),
                    "updated_at": (
                        agent.updated_at.isoformat() if agent.updated_at else None
                    ),
                }
            except Exception as e:
                console.print(f"Error getting agent by path from database: {e}")
                return None
                

    def get_agent_by_fingerprint(self, fingerprint: str) -> Optional[Dict]:
        """Get agent information by fingerprint"""
        with self.db_manager.get_session() as session:
            try:
                agent = session.query(Agent).filter(
                    Agent.fingerprint == fingerprint
                ).first()

                if not agent:
                    return None

                return {
                    "agent_id": agent.agent_id,
                    "agent_path": agent.agent_path,
                    "host": agent.host,
                    "port": agent.port,
                    "framework": agent.framework,
                    "status": agent.status,
                    "is_local": agent.is_local,
                    "fingerprint": agent.fingerprint,
                    "deployed_at": (
                        agent.deployed_at.isoformat() if agent.deployed_at else None
                    ),
                    "last_run": agent.last_run.isoformat() if agent.last_run else None,
                    "run_count": agent.run_count,
                    "success_count": agent.success_count,
                    "error_count": agent.error_count,
                    "created_at": (
                        agent.created_at.isoformat() if agent.created_at else None
                    ),
                    "updated_at": (
                        agent.updated_at.isoformat() if agent.updated_at else None
                    ),
                }
            except Exception as e:
                console.print(f"Error getting agent by fingerprint from database: {e}")
                return None

    def add_remote_agent(
        self,
        agent_id: str,
        agent_path: str,
        framework: str = None,
        fingerprint: str = None,
        status: str = "uploaded",
        agent_name: str = None,
        description: str = None,
        template: str = None,
        version: str = None,
        initialized_at: str = None,
        config_fingerprint: str = None,
        project_id: str = None,
    ) -> Dict:
        """
        Add a remote uploaded agent to the database
        
        Args:
            agent_id: Unique agent identifier
            agent_path: Path to agent directory (local path for reference)
            framework: Framework type
            fingerprint: Agent fingerprint for duplicate detection
            status: Agent status (uploaded, uploading, deployed)
            
        Returns:
            Dictionary with success status and details
        """
        if not agent_id or not agent_path:
            return {
                "success": False,
                "error": "Missing required fields",
                "code": "INVALID_INPUT",
            }

        with self.db_manager.get_session() as session:
            try:
                # Check if agent already exists by ID
                existing_agent = (
                    session.query(Agent).filter(Agent.agent_id == agent_id).first()
                )
                if existing_agent:
                    return {
                        "success": False,
                        "error": f"Agent {agent_id} already exists",
                        "code": "AGENT_EXISTS",
                        "existing_agent": {
                            "agent_id": existing_agent.agent_id,
                            "status": existing_agent.status,
                            "is_local": existing_agent.is_local,
                        }
                    }

                # Check if agent with same fingerprint exists (for duplicate detection)
                if fingerprint:
                    duplicate_agent = (
                        session.query(Agent).filter(Agent.fingerprint == fingerprint).first()
                    )
                    if duplicate_agent:
                        return {
                            "success": False,
                            "error": f"Agent with same fingerprint already exists",
                            "code": "DUPLICATE_FINGERPRINT",
                            "existing_agent": {
                                "agent_id": duplicate_agent.agent_id,
                                "status": duplicate_agent.status,
                                "is_local": duplicate_agent.is_local,
                                "fingerprint": duplicate_agent.fingerprint,
                            }
                        }

                # Create new remote agent record
                new_agent = Agent(
                    agent_id=agent_id,
                    agent_path=str(agent_path),
                    host="remote",  # Remote agents don't have local host/port
                    port=0,  # Remote agents don't have local port
                    framework=framework,
                    status="initialized",  # Local status
                    remote_status=status,  # Remote status
                    is_local=False,  # Mark as remote
                    fingerprint=fingerprint,
                    agent_name=agent_name,
                    description=description,
                    template=template,
                    version=version,
                    initialized_at=initialized_at,
                    config_fingerprint=config_fingerprint,
                    project_id=project_id,
                )

                session.add(new_agent)
                session.commit()

                return {
                    "success": True,
                    "message": f"Remote agent {agent_id} added successfully",
                    "agent_id": agent_id,
                    "status": status,
                    "is_local": False,
                }

            except Exception as e:
                session.rollback()
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "code": "DATABASE_ERROR",
                }

    def update_agent_fingerprint(self, agent_id: str, fingerprint: str) -> bool:
        """Update agent fingerprint"""
        with self.db_manager.get_session() as session:
            try:
                agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                if not agent:
                    return False

                agent.fingerprint = fingerprint
                agent.updated_at = func.current_timestamp()
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                console.print(f"Error updating agent fingerprint: {e}")
                return False
                
    def list_agents(self, status: str = None) -> List[Dict]:
        """List all agents, optionally filtered by status"""
        with self.db_manager.get_session() as session:
            try:
                query = session.query(Agent)
                if status:
                    query = query.filter(Agent.status == status)

                agents = query.order_by(desc(Agent.deployed_at)).all()

                return [
                    {
                        "agent_id": agent.agent_id,
                        "agent_path": agent.agent_path,
                        "host": agent.host,
                        "port": agent.port,
                        "framework": agent.framework,
                        "status": agent.status,
                        "deployed_at": (
                            agent.deployed_at.isoformat() if agent.deployed_at else None
                        ),
                        "last_run": (
                            agent.last_run.isoformat() if agent.last_run else None
                        ),
                        "run_count": agent.run_count,
                        "success_count": agent.success_count,
                        "error_count": agent.error_count,
                        "created_at": (
                            agent.created_at.isoformat() if agent.created_at else None
                        ),
                        "updated_at": (
                            agent.updated_at.isoformat() if agent.updated_at else None
                        ),
                    }
                    for agent in agents
                ]
            except Exception as e:
                console.print(f"Error listing agents from database: {e}")
                return []

    def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status"""
        with self.db_manager.get_session() as session:
            try:
                agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                if not agent:
                    return False

                agent.status = status
                agent.updated_at = func.current_timestamp()
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                console.print(f"Error updating agent status: {e}")
                return False

    def record_agent_run(
        self,
        agent_id: str,
        input_data: Dict,
        output_data: Dict = None,
        success: bool = True,
        error_message: str = None,
        execution_time: float = None,
    ) -> int:
        """Record an agent execution"""
        with self.db_manager.get_session() as session:
            try:
                # Create new run record
                run = AgentRun(
                    agent_id=agent_id,
                    input_data=json.dumps(input_data),
                    output_data=json.dumps(output_data) if output_data else None,
                    success=success,
                    error_message=error_message,
                    execution_time=execution_time,
                    completed_at=func.current_timestamp(),
                )

                session.add(run)
                session.flush()  # Get the ID
                run_id = run.id

                # Update agent statistics
                agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                if agent:
                    agent.run_count += 1
                    agent.last_run = func.current_timestamp()
                    agent.updated_at = func.current_timestamp()

                    if success:
                        agent.success_count += 1
                    else:
                        agent.error_count += 1

                session.commit()
                return run_id
            except Exception as e:
                session.rollback()
                console.print(f"Error recording agent run: {e}")
                return -1

    def get_agent_runs(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Get recent runs for an agent"""
        with self.db_manager.get_session() as session:
            try:
                runs = (
                    session.query(AgentRun)
                    .filter(AgentRun.agent_id == agent_id)
                    .order_by(desc(AgentRun.started_at))
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "id": run.id,
                        "agent_id": run.agent_id,
                        "input_data": (
                            json.loads(run.input_data) if run.input_data else None
                        ),
                        "output_data": (
                            json.loads(run.output_data) if run.output_data else None
                        ),
                        "success": run.success,
                        "error_message": run.error_message,
                        "execution_time": run.execution_time,
                        "started_at": (
                            run.started_at.isoformat() if run.started_at else None
                        ),
                        "completed_at": (
                            run.completed_at.isoformat() if run.completed_at else None
                        ),
                    }
                    for run in runs
                ]
            except Exception as e:
                console.print(f"Error getting agent runs: {e}")
                return []

    def get_agent_stats(self, agent_id: str) -> Dict:
        """Get agent statistics"""
        agent_data = self.get_agent(agent_id)
        if not agent_data:
            return {}

        with self.db_manager.get_session() as session:
            try:
                # Get recent runs for performance calculation
                recent_runs = (
                    session.query(AgentRun)
                    .filter(
                        AgentRun.agent_id == agent_id,
                        AgentRun.execution_time.isnot(None),
                    )
                    .order_by(desc(AgentRun.started_at))
                    .limit(10)
                    .all()
                )

                # Calculate statistics
                total_runs = agent_data["run_count"]
                success_rate = (
                    (agent_data["success_count"] / total_runs * 100)
                    if total_runs > 0
                    else 0
                )

                avg_execution_time = None
                if recent_runs:
                    execution_times = [
                        run.execution_time
                        for run in recent_runs
                        if run.execution_time is not None
                    ]
                    if execution_times:
                        avg_execution_time = sum(execution_times) / len(execution_times)

                return {
                    "agent_id": agent_id,
                    "total_runs": total_runs,
                    "success_count": agent_data["success_count"],
                    "error_count": agent_data["error_count"],
                    "success_rate": round(success_rate, 2),
                    "last_run": agent_data["last_run"],
                    "avg_execution_time": (
                        round(avg_execution_time, 3) if avg_execution_time else None
                    ),
                    "status": agent_data["status"],
                    "deployed_at": agent_data["deployed_at"],
                    "framework": agent_data["framework"],
                }
            except Exception as e:
                console.print(f"Error getting agent stats: {e}")
                return {}

    def cleanup_old_runs(self, days_old: int = 30) -> int:
        """Clean up old run records"""
        with self.db_manager.get_session() as session:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                deleted_count = (
                    session.query(AgentRun)
                    .filter(AgentRun.started_at < cutoff_date)
                    .delete()
                )
                session.commit()
                return deleted_count
            except Exception as e:
                session.rollback()
                console.print(f"Error cleaning up old runs: {e}")
                return 0

    def get_database_stats(self) -> Dict:
        """Get overall database statistics"""
        with self.db_manager.get_session() as session:
            try:
                # Get agent counts by status
                status_counts = {}
                status_results = (
                    session.query(Agent.status, func.count(Agent.agent_id))
                    .group_by(Agent.status)
                    .all()
                )

                for status, count in status_results:
                    status_counts[status] = count

                # Get total runs
                total_runs = session.query(AgentRun).count()

                # Get database size
                db_size = (
                    self.db_manager.db_path.stat().st_size
                    if self.db_manager.db_path.exists()
                    else 0
                )

                return {
                    "total_agents": sum(status_counts.values()),
                    "agent_status_counts": status_counts,
                    "total_runs": total_runs,
                    "database_size_mb": round(db_size / 1024 / 1024, 2),
                    "database_path": str(self.db_manager.db_path.absolute()),
                    "rest_client_configured": self.rest_client is not None,
                }
            except Exception as e:
                console.print(f"Error getting database stats: {e}")
                return {"rest_client_configured": self.rest_client is not None}

    def _allocate_port(self, session, preferred_host: str, preferred_port: int = None) -> int:
        """
        Allocate a port for an agent
        
        Args:
            session: Database session
            preferred_host: Preferred host address
            preferred_port: Preferred port number
            
        Returns:
            Allocated port number or None if no ports available
        """
        # Get currently used ports
        used_ports = []
        existing_agents = session.query(Agent).all()
        for agent in existing_agents:
            if agent.port:
                used_ports.append(agent.port)
        
        # Try preferred port first
        if preferred_port and PortManager.is_port_available(preferred_host, preferred_port):
            return preferred_port
        
        # Auto-allocate available address
        try:
            _, allocated_port = PortManager.allocate_unique_address(used_ports)
            return allocated_port
        except Exception:
            return None

    def update_agent(
        self,
        agent_id: str,
        host: str = None,
        port: int = None,
        framework: str = None,
        status: str = None,
        remote_status: str = None,
        fingerprint: str = None,
        deployed_at: datetime = None,
        auto_port: bool = False,
        preferred_host: str = "127.0.0.1",
        preferred_port: int = None,
    ) -> Dict:
        """
        Update an existing agent's deployment information
        
        Args:
            agent_id: Unique agent identifier
            host: Host address (optional)
            port: Port number (optional)
            framework: Framework type (optional)
            status: Local deployment status (optional)
            remote_status: Remote deployment status (optional)
            fingerprint: Agent fingerprint (optional)
            deployed_at: Deployment timestamp (optional)
            auto_port: Whether to auto-allocate port if not provided
            preferred_host: Preferred host for auto-allocation
            preferred_port: Preferred port for auto-allocation
            
        Returns:
            Dictionary with success status and updated information
        """
        if not agent_id:
            return {
                "success": False,
                "error": "Agent ID is required",
                "code": "INVALID_INPUT",
            }

        with self.db_manager.get_session() as session:
            try:
                # Find existing agent
                existing_agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                
                if not existing_agent:
                    return {
                        "success": False,
                        "error": f"Agent {agent_id} not found",
                        "code": "AGENT_NOT_FOUND",
                    }
                
                # Handle auto port allocation if requested
                allocated_host = host
                allocated_port = port
                
                if auto_port and port is None:
                    # Auto-allocate port
                    allocated_host = preferred_host
                    allocated_port = self._allocate_port(session, preferred_host, preferred_port)
                    
                    if allocated_port is None:
                        return {
                            "success": False,
                            "error": "No available ports for auto-allocation",
                            "code": "NO_PORTS_AVAILABLE",
                        }
                
                # Update fields that are provided
                if host is not None:
                    existing_agent.host = host
                elif allocated_host is not None:
                    existing_agent.host = allocated_host
                    
                if port is not None:
                    existing_agent.port = port
                elif allocated_port is not None:
                    existing_agent.port = allocated_port
                    
                if framework is not None:
                    if hasattr(framework, 'value'):
                        existing_agent.framework = framework.value
                    else:
                        existing_agent.framework = str(framework)
                        
                if status is not None:
                    existing_agent.status = status
                    
                if remote_status is not None:
                    existing_agent.remote_status = remote_status
                    
                if fingerprint is not None:
                    existing_agent.fingerprint = fingerprint
                    
                if deployed_at is not None:
                    existing_agent.deployed_at = deployed_at
                elif status in ["serving", "deployed"] or remote_status in ["uploaded", "deploying", "deployed"]:
                    # Auto-set deployed_at if status indicates deployment
                    existing_agent.deployed_at = datetime.now()
                
                # Update timestamp
                existing_agent.updated_at = datetime.now()
                
                session.commit()
                
                return {
                    "success": True,
                    "message": f"Agent {agent_id} updated successfully",
                    "agent_id": agent_id,
                    "host": existing_agent.host,
                    "port": existing_agent.port,
                    "status": existing_agent.status,
                    "remote_status": existing_agent.remote_status,
                    "framework": existing_agent.framework,
                    "allocated_host": allocated_host if auto_port else None,
                    "allocated_port": allocated_port if auto_port else None,
                }
                
            except Exception as e:
                session.rollback()
                return {
                    "success": False,
                    "error": f"Database error: {str(e)}",
                    "code": "DATABASE_ERROR",
                }

    def validate_agent_id(self, agent_id: str) -> Dict:
        """
        Validate that an agent ID exists in the database
        
        Args:
            agent_id: Agent ID to validate
            
        Returns:
            Dictionary with validation result
        """
        if not agent_id:
            return {
                "valid": False,
                "error": "Agent ID is required",
                "code": "MISSING_AGENT_ID",
            }
        
        with self.db_manager.get_session() as session:
            try:
                existing_agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                
                if existing_agent:
                    return {
                        "valid": True,
                        "agent": {
                            "agent_id": existing_agent.agent_id,
                            "agent_name": existing_agent.agent_name,
                            "agent_path": existing_agent.agent_path,
                            "status": existing_agent.status,
                            "remote_status": existing_agent.remote_status,
                            "framework": existing_agent.framework,
                        }
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"Agent ID '{agent_id}' not found in database",
                        "code": "AGENT_NOT_FOUND",
                        "suggestion": "Use 'runagent config --register-agent .' to register a modified agent"
                    }
                    
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Database error: {str(e)}",
                    "code": "DATABASE_ERROR",
                }

    def validate_agent_path(self, agent_id: str, current_path: str) -> Dict:
        """
        Validate that the agent path in database matches the current folder path
        
        Args:
            agent_id: Agent ID to validate
            current_path: Current folder path being uploaded
            
        Returns:
            Dictionary with validation result
        """
        if not agent_id or not current_path:
            return {
                "valid": False,
                "error": "Agent ID and current path are required",
                "code": "MISSING_PARAMETERS",
            }
        
        with self.db_manager.get_session() as session:
            try:
                existing_agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                
                if not existing_agent:
                    return {
                        "valid": False,
                        "error": f"Agent ID '{agent_id}' not found in database",
                        "code": "AGENT_NOT_FOUND",
                    }
                
                # Normalize paths for comparison
                db_path = str(Path(existing_agent.agent_path).resolve()) if existing_agent.agent_path else ""
                current_path_normalized = str(Path(current_path).resolve())
                
                if db_path == current_path_normalized:
                    return {
                        "valid": True,
                        "message": "Agent path matches database record"
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"Agent path mismatch detected",
                        "code": "PATH_MISMATCH",
                        "details": {
                            "db_path": db_path,
                            "current_path": current_path_normalized,
                            "agent_id": agent_id
                        },
                        "suggestion": "Use 'runagent config --register-agent .' to update the agent location in database"
                    }
                    
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Database error: {str(e)}",
                    "code": "DATABASE_ERROR",
                }

    def get_agent_address(self, agent_id: str) -> Optional[Tuple[str, int]]:
        """
        Get host and port for a specific agent

        Args:
            agent_id: Agent identifier

        Returns:
            Tuple of (host, port) if found, None otherwise
        """
        agent_data = self.get_agent(agent_id)
        if agent_data:
            return agent_data.get("host"), agent_data.get("port")
        return None

    def close(self):
        """Close database connections"""
        self.db_manager.close()


    def force_delete_agent(self, agent_id: str) -> Dict:
        """
        Force delete agent from database (bypasses the normal deletion restriction)
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Dictionary with success status and details
        """
        with self.db_manager.get_session() as session:
            try:
                # Find the agent
                agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
                
                if not agent:
                    return {
                        "success": False,
                        "error": f"Agent {agent_id} not found",
                        "code": "AGENT_NOT_FOUND",
                    }
                
                # Store agent info for the response
                agent_info = {
                    "agent_id": agent.agent_id,
                    "framework": agent.framework,
                    "deployed_at": agent.deployed_at.isoformat() if agent.deployed_at else None,
                }
                
                # Delete the agent (CASCADE will handle related AgentRun records)
                session.delete(agent)
                session.commit()
                
                console.print(f"🗑️ [green]Force deleted agent: {agent_id}[/green]")
                
                return {
                    "success": True,
                    "message": f"Agent {agent_id} force deleted successfully",
                    "deleted_agent": agent_info,
                    "operation": "force_delete",
                }
                
            except Exception as e:
                session.rollback()
                console.print(f"❌ [red]Error force deleting agent {agent_id}: {str(e)}[/red]")
                return {
                    "success": False,
                    "error": f"Failed to force delete agent: {str(e)}",
                    "code": "DELETE_ERROR",
                }


    def record_agent_log(
        self,
        agent_id: str,
        log_level: str,
        message: str,
        execution_id: str = None
    ) -> int:
        """Record an agent log entry"""
        with self.db_manager.get_session() as session:
            try:
                # Create new log record
                log_entry = AgentLog(
                    agent_id=agent_id,
                    log_level=log_level.upper(),
                    message=message,
                    execution_id=execution_id,
                    created_at=func.current_timestamp()
                )

                session.add(log_entry)
                session.flush()  # Get the ID
                log_id = log_entry.id
                session.commit()
                return log_id
            except Exception as e:
                session.rollback()
                console.print(f"Error recording agent log: {e}")
                return -1

    def get_agent_logs(
        self, 
        agent_id: str, 
        limit: int = 100,
        log_level: str = None,
        execution_id: str = None
    ) -> List[Dict]:
        """Get agent logs with optional filtering"""
        with self.db_manager.get_session() as session:
            try:
                query = session.query(AgentLog).filter(
                    AgentLog.agent_id == agent_id
                )
                
                if log_level:
                    query = query.filter(AgentLog.log_level == log_level.upper())
                
                if execution_id:
                    query = query.filter(AgentLog.execution_id == execution_id)
                
                logs = query.order_by(desc(AgentLog.created_at)).limit(limit).all()

                return [
                    {
                        "id": log.id,
                        "agent_id": log.agent_id,
                        "log_level": log.log_level,
                        "message": log.message,
                        "execution_id": log.execution_id,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    }
                    for log in logs
                ]
            except Exception as e:
                console.print(f"Error getting agent logs: {e}")
                return []

    def cleanup_old_logs(self, days_old: int = 7) -> int:
        """Clean up old log records (logs are more ephemeral than runs)"""
        with self.db_manager.get_session() as session:
            try:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                deleted_count = (
                    session.query(AgentLog)
                    .filter(AgentLog.created_at < cutoff_date)
                    .delete()
                )
                session.commit()
                console.print(f"🧹 [green]Cleaned up {deleted_count} old log entries[/green]")
                return deleted_count
            except Exception as e:
                session.rollback()
                console.print(f"Error cleaning up old logs: {e}")
                return 0

    # User Metadata Methods
    def set_user_metadata(self, key: str, value: Any) -> bool:
        """
        Set user metadata key-value pair
        
        Args:
            key: Metadata key (e.g., 'api_key', 'base_url', 'user_email')
            value: Metadata value (will be JSON-serialized)
            
        Returns:
            True if successful, False otherwise
        """
        with self.db_manager.get_session() as session:
            try:
                # Serialize value to JSON
                value_json = json.dumps(value)
                
                # Check if key exists
                metadata = session.query(UserMetadata).filter(
                    UserMetadata.key == key
                ).first()
                
                if metadata:
                    # Update existing
                    metadata.value = value_json
                    metadata.updated_at = func.current_timestamp()
                else:
                    # Create new
                    metadata = UserMetadata(
                        key=key,
                        value=value_json
                    )
                    session.add(metadata)
                
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"Error setting user metadata: {e}")
                return False

    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get user metadata value by key
        
        Args:
            key: Metadata key
            default: Default value if key doesn't exist
            
        Returns:
            Deserialized metadata value or default
        """
        with self.db_manager.get_session() as session:
            try:
                metadata = session.query(UserMetadata).filter(
                    UserMetadata.key == key
                ).first()
                
                if not metadata:
                    return default
                
                # Deserialize JSON value
                return json.loads(metadata.value)
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"Error getting user metadata: {e}")
                return default

    def get_all_user_metadata(self) -> Dict[str, Any]:
        """
        Get all user metadata as a dictionary
        
        Returns:
            Dictionary with all metadata key-value pairs
        """
        with self.db_manager.get_session() as session:
            try:
                metadata_records = session.query(UserMetadata).all()
                
                result = {}
                for record in metadata_records:
                    try:
                        result[record.key] = json.loads(record.value)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, store as string
                        result[record.key] = record.value
                
                return result
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"Error getting all user metadata: {e}")
                return {}

    def get_active_project_id(self) -> t.Optional[str]:
        """
        Get the active project ID from user metadata
        
        Returns:
            Active project ID if found, None otherwise
        """
        with self.db_manager.get_session() as session:
            try:
                metadata = session.query(UserMetadata).filter(
                    UserMetadata.key == "active_project_id"
                ).first()
                
                if metadata:
                    return metadata.value
                return None
            except Exception as e:
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"Error getting active project ID: {e}")
                return None

    def delete_user_metadata(self, key: str) -> bool:
        """
        Delete user metadata by key
        
        Args:
            key: Metadata key to delete
            
        Returns:
            True if successful, False otherwise
        """
        with self.db_manager.get_session() as session:
            try:
                metadata = session.query(UserMetadata).filter(
                    UserMetadata.key == key
                ).first()
                
                if not metadata:
                    return False
                
                session.delete(metadata)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"Error deleting user metadata: {e}")
                return False

    def clear_all_user_metadata(self) -> bool:
        """
        Clear all user metadata
        
        Returns:
            True if successful, False otherwise
        """
        with self.db_manager.get_session() as session:
            try:
                session.query(UserMetadata).delete()
                session.commit()
                console.print("🧹 [green]Cleared all user metadata[/green]")
                return True
            except Exception as e:
                session.rollback()
                if os.getenv('DISABLE_TRY_CATCH'):
                    raise
                console.print(f"Error clearing user metadata: {e}")
                return False
