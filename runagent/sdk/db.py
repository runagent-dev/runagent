import json
import os
import uuid
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

from runagent.constants import LOCAL_CACHE_DIRECTORY
from runagent.utils.port import PortManager


console = Console()


Base = declarative_base()


class Agent(Base):
    """Agent model - Enhanced with remote upload tracking"""

    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True)
    agent_path = Column(String, nullable=False)
    host = Column(String, nullable=False, default="localhost")
    port = Column(Integer, nullable=False, default=8000)
    framework = Column(String)
    status = Column(String, default="deployed")  # deployed, uploaded, uploading
    is_local = Column(Boolean, default=True)  # True for local agents, False for remote uploads
    fingerprint = Column(String, nullable=True)  # Agent folder fingerprint for duplicate detection
    deployed_at = Column(DateTime, default=func.current_timestamp())
    last_run = Column(DateTime)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

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

class DBManager:
    """Low-level database manager for SQLAlchemy operations"""

    def __init__(self, db_path: Path = None):
        """
        Initialize the database manager

        Args:
            db_path: Path to the SQLite database file
        """
        if db_path is None:
            db_path = Path(LOCAL_CACHE_DIRECTORY) / "runagent_local.db"

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

        # System resource allocation limits based on deployment tier
        self._deployment_config = self._load_system_constraints()

        # Cache for limits to avoid repeated API calls (5 minutes cache)
        self._limits_cache = None
        self._cache_expiry = None

    def _load_system_constraints(self) -> Dict[str, Any]:
        """Load system deployment constraints and resource limits"""
        # Obfuscated calculation to make default limit less obvious
        tier_multiplier = 0x1  # Base tier
        resource_factor = int("101", 2)  # Convert binary string to int (5)

        # Calculate deployment limits based on system architecture
        base_limit = resource_factor  # This gives us 5
        deployment_ceiling = base_limit  # Keep it as 5

        # Apply enterprise scaling factor (no-op in this case)
        enterprise_modifier = lambda x: x
        final_limit = enterprise_modifier(deployment_ceiling)

        return {
            "max_concurrent_instances": final_limit,
            "resource_tier": "standard",
            "allocation_strategy": "fixed_pool",
        }

    def _get_default_limit(self) -> int:
        """Get the default agent limit (obfuscated calculation)"""
        return self._deployment_config["max_concurrent_instances"]

    def _should_check_api_before_adding(self, current_count: int) -> bool:
        """Determine if we should check API before adding an agent"""
        default_limit = self._get_default_limit()

        # Only check API if we're at or exceeding default limits
        return current_count >= default_limit

    def _check_enhanced_limits_with_fallback(self) -> Dict:
        """
        Check enhanced limits via RestClient API with fallback to default limits

        Returns:
            Dictionary with limit information
        """
        # Check cache first (5 minutes cache)
        if (
            self._limits_cache
            and self._cache_expiry
            and datetime.now() < self._cache_expiry
        ):
            return self._limits_cache

        default_limit = self._get_default_limit()

        # If no RestClient available, use default limits
        if not self.rest_client:
            result = {
                "limit": default_limit,
                "enhanced": False,
                "source": "default",
                "api_available": False,
                "api_validated": False,
                "error": "No RestClient configured",
            }
            return result

        try:
            console.print("🔍 [dim]Checking enhanced limits via API...[/dim]")

            # Use RestClient to get limits
            limits_data = self.rest_client.get_local_db_limits()

            if limits_data.get("success"):
                max_agents = limits_data.get("max_agents", default_limit)
                enhanced = limits_data.get("enhanced_limits", False)

                # Handle unlimited case
                if max_agents == -1:
                    max_agents = 999  # Practical unlimited
                    enhanced = True

                result = {
                    "limit": max_agents,
                    "enhanced": enhanced,
                    "source": "api" if enhanced else "default",
                    "api_available": True,
                    "api_validated": limits_data.get("api_validated", False),
                    "tier_info": limits_data.get("tier_info", {}),
                    "features": limits_data.get("features", []),
                    "expires_at": limits_data.get("expires_at"),
                    "unlimited": max_agents == 999,
                }

                # Cache for 5 minutes
                self._limits_cache = result
                self._cache_expiry = datetime.now() + timedelta(minutes=5)

                if enhanced:
                    console.print(
                        f"🔑 [green]Enhanced limits active: {max_agents} agents[/green]"
                    )
                else:
                    console.print(
                        f"🔑 [yellow]Using default limits: {max_agents} agents[/yellow]"
                    )

                return result

            else:
                # API call failed, use default limits
                error_msg = limits_data.get("error", "Unknown API error")
                result = {
                    "limit": default_limit,
                    "enhanced": False,
                    "source": "default",
                    "api_available": True,
                    "api_validated": limits_data.get("api_validated", False),
                    "error": error_msg,
                }

                console.print(
                    f"[yellow]⚠️ API limit check failed: {error_msg} - using default limits[/yellow]"
                )
                return result

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            # Exception during API call, fallback to default
            result = {
                "limit": default_limit,
                "enhanced": False,
                "source": "default",
                "api_available": False,
                "api_validated": False,
                "error": f"API check exception: {str(e)}",
            }

            console.print(
                f"[red]❌ Error checking enhanced limits: {str(e)} - using default limits[/red]"
            )
            return result

    def clear_limits_cache(self):
        """Clear the cached enhanced limits to force refresh"""
        self._limits_cache = None
        self._cache_expiry = None
        if self.rest_client:
            self.rest_client.clear_limits_cache()
        console.print("🔄 [dim]Enhanced limits cache cleared[/dim]")

    def get_current_tier_info(self) -> Dict:
        """Get information about current deployment tier and limits"""
        default_limit = self._get_default_limit()

        # Get current limit info (may trigger API call)
        limit_info = self._check_enhanced_limits_with_fallback()

        return {
            "default_limit": default_limit,
            "current_limit": limit_info["limit"],
            "enhanced_via_api": limit_info.get("enhanced", False),
            "limit_source": limit_info.get("source", "default"),
            "api_available": limit_info.get("api_available", False),
            "api_validated": limit_info.get("api_validated", False),
            "tier_info": limit_info.get("tier_info", {}),
            "unlimited": limit_info.get("unlimited", False),
            "api_error": limit_info.get("error"),
            "cache_expires": (
                self._cache_expiry.isoformat() if self._cache_expiry else None
            ),
            "rest_client_configured": self.rest_client is not None,
        }

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


    def _load_system_constraints(self) -> Dict[str, Any]:
        """Load system deployment constraints and resource limits"""
        # Obfuscated calculation to make default limit less obvious
        tier_multiplier = 0x1  # Base tier
        resource_factor = int("101", 2)  # Convert binary string to int (5)

        # Calculate deployment limits based on system architecture
        base_limit = resource_factor  # This gives us 5
        deployment_ceiling = base_limit  # Keep it as 5

        # Apply enterprise scaling factor (no-op in this case)
        enterprise_modifier = lambda x: x
        final_limit = enterprise_modifier(deployment_ceiling)

        return {
            "max_concurrent_instances": final_limit,
            "resource_tier": "standard",
            "allocation_strategy": "fixed_pool",
        }

    def _get_default_limit(self) -> int:
        """Get the default agent limit (obfuscated calculation)"""
        return self._deployment_config["max_concurrent_instances"]

    def _should_check_api_before_adding(self, current_count: int) -> bool:
        """Determine if we should check API before adding an agent"""
        default_limit = self._get_default_limit()

        # Only check API if we're at or exceeding default limits
        return current_count >= default_limit

    def _check_enhanced_limits_with_fallback(self) -> Dict:
        """
        Check enhanced limits via RestClient API with fallback to default limits

        Returns:
            Dictionary with limit information
        """
        # Check cache first (5 minutes cache)
        if (
            self._limits_cache
            and self._cache_expiry
            and datetime.now() < self._cache_expiry
        ):
            return self._limits_cache

        default_limit = self._get_default_limit()

        # If no RestClient available, use default limits
        if not self.rest_client:
            result = {
                "limit": default_limit,
                "enhanced": False,
                "source": "default",
                "api_available": False,
                "api_validated": False,
                "error": "No RestClient configured",
            }
            return result

        try:
            console.print("🔍 [dim]Checking enhanced limits via API...[/dim]")

            # Use RestClient to get limits
            limits_data = self.rest_client.get_local_db_limits()

            if limits_data.get("success"):
                max_agents = limits_data.get("max_agents", default_limit)
                enhanced = limits_data.get("enhanced_limits", False)

                # Handle unlimited case
                if max_agents == -1:
                    max_agents = 999  # Practical unlimited
                    enhanced = True

                result = {
                    "limit": max_agents,
                    "enhanced": enhanced,
                    "source": "api" if enhanced else "default",
                    "api_available": True,
                    "api_validated": limits_data.get("api_validated", False),
                    "tier_info": limits_data.get("tier_info", {}),
                    "features": limits_data.get("features", []),
                    "expires_at": limits_data.get("expires_at"),
                    "unlimited": max_agents == 999,
                }

                # Cache for 5 minutes
                self._limits_cache = result
                self._cache_expiry = datetime.now() + timedelta(minutes=5)

                if enhanced:
                    console.print(
                        f"🔑 [green]Enhanced limits active: {max_agents} agents[/green]"
                    )
                else:
                    console.print(
                        f"🔑 [yellow]Using default limits: {max_agents} agents[/yellow]"
                    )

                return result

            else:
                # API call failed, use default limits
                error_msg = limits_data.get("error", "Unknown API error")
                result = {
                    "limit": default_limit,
                    "enhanced": False,
                    "source": "default",
                    "api_available": True,
                    "api_validated": limits_data.get("api_validated", False),
                    "error": error_msg,
                }

                console.print(
                    f"[yellow]⚠️ API limit check failed: {error_msg} - using default limits[/yellow]"
                )
                return result

        except Exception as e:
            if os.getenv('DISABLE_TRY_CATCH'):
                raise
            # Exception during API call, fallback to default
            result = {
                "limit": default_limit,
                "enhanced": False,
                "source": "default",
                "api_available": False,
                "api_validated": False,
                "error": f"API check exception: {str(e)}",
            }

            console.print(
                f"[red]❌ Error checking enhanced limits: {str(e)} - using default limits[/red]"
            )
            return result

    def add_agent(
        self,
        agent_id: str,
        agent_path: str,
        host: str = "localhost",
        port: int = 8450,
        framework: str = None,
        status: str = "deployed",
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
                # Check current agent count
                current_count = session.query(Agent).count()

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

                # Smart limit checking
                default_limit = self._get_default_limit()

                # Phase 1: Check if we're within default limits (no API call needed)
                if current_count < default_limit:
                    console.print(
                        f"🟢 Adding agent within default limits ({current_count + 1}/{default_limit})"
                    )

                    # Proceed without API check
                    new_agent = Agent(
                        agent_id=agent_id,
                        agent_path=str(agent_path),
                        host=host,
                        port=port,
                        framework=framework,
                        status=status,
                    )

                    session.add(new_agent)
                    session.commit()

                    return {
                        "success": True,
                        "message": f"Agent {agent_id} added successfully (within default limits)",
                        "current_count": current_count + 1,
                        "limit_source": "default",
                        "api_check_performed": False,
                    }

                # Phase 2: At or above default limit - check API for enhanced limits
                console.print(
                    f"🟡 At default limit ({current_count}/{default_limit}) - checking for enhanced limits..."
                )

                limit_info = self._check_enhanced_limits_with_fallback()
                max_capacity = limit_info["limit"]

                # Check if we can still add within enhanced limits
                if current_count >= max_capacity:
                    oldest_agent = (
                        session.query(Agent).order_by(Agent.deployed_at).first()
                    )

                    # Provide helpful error message based on API availability
                    if not self.rest_client:
                        error_message = f"Maximum {max_capacity} agents allowed. Configure RestClient with API key for enhanced limits."
                        suggestion = "Configure RestClient with valid API key to potentially increase limits"
                    elif not limit_info.get("api_validated", False):
                        error_message = f"Maximum {max_capacity} agents allowed. API key invalid or not configured."
                        suggestion = "Verify API key configuration in RestClient"
                    else:
                        error_message = f"Maximum {max_capacity} agents allowed. Database is at capacity ({current_count}/{max_capacity} agents)."
                        suggestion = (
                            f"Consider replacing the oldest agent: {oldest_agent.agent_id}"
                            if oldest_agent
                            else "Database cleanup needed"
                        )

                    return {
                        "success": False,
                        "error": error_message,
                        "code": "DATABASE_FULL",
                        "current_count": current_count,
                        "max_allowed": max_capacity,
                        "limit_info": limit_info,
                        "oldest_agent": (
                            {
                                "agent_id": oldest_agent.agent_id,
                                "deployed_at": (
                                    oldest_agent.deployed_at.isoformat()
                                    if oldest_agent.deployed_at
                                    else None
                                ),
                            }
                            if oldest_agent
                            else None
                        ),
                        "suggestion": suggestion,
                    }

                # Enhanced limits allow the addition
                new_agent = Agent(
                    agent_id=agent_id,
                    agent_path=str(agent_path),
                    host=host,
                    port=port,
                    framework=framework,
                    status=status,
                )

                session.add(new_agent)
                session.commit()

                limit_source = "enhanced" if limit_info.get("enhanced") else "default"
                console.print(
                    f"🟢 Agent added with {limit_source} limits ({current_count + 1}/{max_capacity})"
                )

                return {
                    "success": True,
                    "message": f"Agent {agent_id} added successfully ({limit_source} limits)",
                    "current_count": current_count + 1,
                    "max_allowed": max_capacity,
                    "remaining_slots": (
                        max_capacity - (current_count + 1)
                        if max_capacity != 999
                        else "unlimited"
                    ),
                    "limit_info": limit_info,
                    "api_check_performed": True,
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
        Replace an existing agent with a new one

        Args:
            old_agent_id: Agent ID to replace
            new_agent_id: New agent ID
            agent_path: Path to agent directory
            host: Host address
            port: Port number
            framework: Framework type

        Returns:
            Dictionary with success status and details
        """
        if not old_agent_id or not new_agent_id or not agent_path:
            return {
                "success": False,
                "error": "Missing required fields",
                "code": "INVALID_INPUT",
            }

        with self.db_manager.get_session() as session:
            try:
                # Check if old agent exists
                old_agent = (
                    session.query(Agent).filter(Agent.agent_id == old_agent_id).first()
                )
                if not old_agent:
                    return {
                        "success": False,
                        "error": f"Agent {old_agent_id} not found for replacement",
                        "code": "AGENT_NOT_FOUND",
                    }

                # Check if new agent ID already exists
                existing_new_agent = (
                    session.query(Agent).filter(Agent.agent_id == new_agent_id).first()
                )
                if existing_new_agent:
                    return {
                        "success": False,
                        "error": f"New agent ID {new_agent_id} already exists",
                        "code": "NEW_AGENT_EXISTS",
                    }

                # Update the existing record
                old_agent.agent_id = new_agent_id
                old_agent.agent_path = str(agent_path)
                old_agent.host = host
                old_agent.port = port
                old_agent.framework = framework
                old_agent.deployed_at = func.current_timestamp()
                old_agent.updated_at = func.current_timestamp()
                old_agent.status = "deployed"
                old_agent.run_count = 0
                old_agent.success_count = 0
                old_agent.error_count = 0

                # Update run records to point to new agent ID
                session.query(AgentRun).filter(
                    AgentRun.agent_id == old_agent_id
                ).update({"agent_id": new_agent_id})

                session.commit()

                return {
                    "success": True,
                    "message": f"Agent {old_agent_id} replaced with {new_agent_id}",
                    "old_agent_id": old_agent_id,
                    "new_agent_id": new_agent_id,
                    "operation": "replace",
                }

            except Exception as e:
                session.rollback()
                return {
                    "success": False,
                    "error": f"Replacement failed: {str(e)}",
                    "code": "REPLACE_ERROR",
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
        console.print(f"💡 Use 'replace_agent()' to replace this agent with a new one.")
        return False

    def get_database_capacity_info(self) -> Dict:
        """Get database capacity information with smart limit checking"""
        with self.db_manager.get_session() as session:
            try:
                current_count = session.query(Agent).count()
                default_limit = self._get_default_limit()

                # Only check API if we're at or near limits
                if self._should_check_api_before_adding(current_count):
                    limit_info = self._check_enhanced_limits_with_fallback()
                    max_capacity = limit_info["limit"]
                    enhanced_info = limit_info
                else:
                    max_capacity = default_limit
                    enhanced_info = {
                        "limit": default_limit,
                        "enhanced": False,
                        "source": "default",
                        "api_available": bool(self.rest_client),
                        "api_validated": False,
                    }

                agents = session.query(Agent).order_by(Agent.deployed_at).all()

                return {
                    "current_count": current_count,
                    "max_capacity": max_capacity,
                    "default_limit": default_limit,
                    "remaining_slots": (
                        max(0, max_capacity - current_count)
                        if max_capacity != 999
                        else "unlimited"
                    ),
                    "is_full": current_count >= max_capacity,
                    "limit_info": enhanced_info,
                    "agents": [
                        {
                            "agent_id": agent.agent_id,
                            "deployed_at": (
                                agent.deployed_at.isoformat()
                                if agent.deployed_at
                                else None
                            ),
                            "framework": agent.framework,
                            "status": agent.status,
                        }
                        for agent in agents
                    ],
                    "oldest_agent": (
                        {
                            "agent_id": agents[0].agent_id,
                            "deployed_at": (
                                agents[0].deployed_at.isoformat()
                                if agents[0].deployed_at
                                else None
                            ),
                        }
                        if agents
                        else None
                    ),
                    "newest_agent": (
                        {
                            "agent_id": agents[-1].agent_id,
                            "deployed_at": (
                                agents[-1].deployed_at.isoformat()
                                if agents[-1].deployed_at
                                else None
                            ),
                        }
                        if agents
                        else None
                    ),
                    "rest_client_configured": self.rest_client is not None,
                }
            except Exception as e:
                default_limit = self._get_default_limit()
                return {
                    "error": f"Failed to get capacity info: {str(e)}",
                    "current_count": 0,
                    "max_capacity": default_limit,
                    "default_limit": default_limit,
                    "remaining_slots": default_limit,
                    "is_full": False,
                    "rest_client_configured": self.rest_client is not None,
                }

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
        status: str = "uploaded"
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
                    status=status,
                    is_local=False,  # Mark as remote
                    fingerprint=fingerprint,
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

    def add_agent_with_auto_port(
        self,
        agent_id: str,
        agent_path: str,
        framework: str = None,
        status: str = "deployed",
        preferred_host: str = "127.0.0.1",
        preferred_port: int = None,
    ) -> Dict:
        if hasattr(framework, 'value'):
            framework = framework.value
        elif framework is not None:
            framework = str(framework)
        """
        Add a new agent with automatic port allocation

        Args:
            agent_id: Unique agent identifier
            agent_path: Path to agent directory
            framework: Framework type (langchain, langgraph, etc.)
            status: Initial status
            preferred_host: Preferred host (default: 127.0.0.1)
            preferred_port: Preferred port (auto-allocated if None)

        Returns:
            Dictionary with success status and allocated address details
        """
        if not agent_id or not agent_path:
            return {
                "success": False,
                "error": "Missing required fields",
                "code": "INVALID_INPUT",
            }

        with self.db_manager.get_session() as session:
            try:
                # Check current agent count for capacity management
                current_count = session.query(Agent).count()

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


                # Get currently used ports to avoid conflicts
                used_ports = []
                existing_agents = session.query(Agent).all()
                for agent in existing_agents:
                    if agent.port:
                        used_ports.append(agent.port)

                # Allocate host and port
                if preferred_port and PortManager.is_port_available(preferred_host, preferred_port):
                    # Use preferred port if available
                    allocated_host = preferred_host
                    allocated_port = preferred_port
                    console.print(f"🎯 Using preferred address: [blue]{allocated_host}:{allocated_port}[/blue]")
                else:
                    # Auto-allocate available address
                    allocated_host, allocated_port = PortManager.allocate_unique_address(used_ports)

                # Smart limit checking (existing logic)
                default_limit = self._get_default_limit()

                # Phase 1: Check if we're within default limits (no API call needed)
                if current_count < default_limit:
                    console.print(
                        f"🟢 Adding agent within default limits ({current_count + 1}/{default_limit})"
                    )
                    console.print(f"🔌 Allocated address: [blue]{allocated_host}:{allocated_port}[/blue]")

                    # Proceed without API check
                    new_agent = Agent(
                        agent_id=agent_id,
                        agent_path=str(agent_path),
                        host=allocated_host,
                        port=allocated_port,
                        framework=framework,
                        status=status,
                    )

                    session.add(new_agent)
                    session.commit()

                    return {
                        "success": True,
                        "message": f"Agent {agent_id} added successfully with auto-allocated address",
                        "current_count": current_count + 1,
                        "limit_source": "default",
                        "api_check_performed": False,
                        "allocated_host": allocated_host,
                        "allocated_port": allocated_port,
                        "address": f"{allocated_host}:{allocated_port}",
                    }

                # Phase 2: At or above default limit - check API for enhanced limits
                console.print(
                    f"🟡 At default limit ({current_count}/{default_limit}) - checking for enhanced limits..."
                )

                limit_info = self._check_enhanced_limits_with_fallback()
                max_capacity = limit_info["limit"]

                # Check if we can still add within enhanced limits
                if current_count >= max_capacity:
                    oldest_agent = (
                        session.query(Agent).order_by(Agent.deployed_at).first()
                    )

                    # Provide helpful error message based on API availability
                    if not self.rest_client:
                        error_message = f"Maximum {max_capacity} agents allowed. Configure RestClient with API key for enhanced limits."
                        suggestion = "Configure RestClient with valid API key to potentially increase limits"
                    elif not limit_info.get("api_validated", False):
                        error_message = f"Maximum {max_capacity} agents allowed. API key invalid or not configured."
                        suggestion = "Verify API key configuration in RestClient"
                    else:
                        error_message = f"Maximum {max_capacity} agents allowed. Database is at capacity ({current_count}/{max_capacity} agents)."
                        suggestion = (
                            f"Consider replacing the oldest agent: {oldest_agent.agent_id}"
                            if oldest_agent
                            else "Database cleanup needed"
                        )

                    return {
                        "success": False,
                        "error": error_message,
                        "code": "DATABASE_FULL",
                        "current_count": current_count,
                        "max_allowed": max_capacity,
                        "limit_info": limit_info,
                        "oldest_agent": (
                            {
                                "agent_id": oldest_agent.agent_id,
                                "deployed_at": (
                                    oldest_agent.deployed_at.isoformat()
                                    if oldest_agent.deployed_at
                                    else None
                                ),
                            }
                            if oldest_agent
                            else None
                        ),
                        "suggestion": suggestion,
                    }

                # Enhanced limits allow the addition
                console.print(f"🔌 Allocated address: [blue]{allocated_host}:{allocated_port}[/blue]")
                
                new_agent = Agent(
                    agent_id=agent_id,
                    agent_path=str(agent_path),
                    host=allocated_host,
                    port=allocated_port,
                    framework=framework,
                    status=status,
                )

                session.add(new_agent)
                session.commit()

                limit_source = "enhanced" if limit_info.get("enhanced") else "default"
                console.print(
                    f"🟢 Agent added with {limit_source} limits ({current_count + 1}/{max_capacity})"
                )

                return {
                    "success": True,
                    "message": f"Agent {agent_id} added successfully with auto-allocated address ({limit_source} limits)",
                    "current_count": current_count + 1,
                    "max_allowed": max_capacity,
                    "remaining_slots": (
                        max_capacity - (current_count + 1)
                        if max_capacity != 999
                        else "unlimited"
                    ),
                    "limit_info": limit_info,
                    "api_check_performed": True,
                    "allocated_host": allocated_host,
                    "allocated_port": allocated_port,
                    "address": f"{allocated_host}:{allocated_port}",
                }

            except Exception as e:
                session.rollback()
                return {
                    "success": False,
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
