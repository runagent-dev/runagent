# Pydantic schema for runagent.config.json
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field



class EntryPointType(Enum):
    """Enum for different types of agent entrypoints"""
    GENERIC = "generic"
    GENERIC_STREAM = "generic_stream"


class TemplateSource(BaseModel):
    """Template source configuration"""

    repo_url: str = Field(..., description="GitHub repository URL")
    author: str = Field(..., description="Template Author name")
    path: str = Field(..., description="Path to template in repository")


class EntryPoint(BaseModel):
    """Entrypoint configuration"""

    file: str = Field(..., description="Entrypoint file")
    module: str = Field(..., description="Entrypoint module name")
    type: EntryPointType = Field(..., description="Entrypoint type")


class AgentArchitecture(BaseModel):
    """Agent architecture configuration"""

    entrypoints: List[EntryPoint] = Field(..., description="List of entrypoints")


class RunAgentConfig(BaseModel):
    """Schema for runagent.config.json"""

    agent_name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    framework: str = Field(..., description="Framework used (langchain, etc)")
    template: str = Field(..., description="Template name")
    version: str = Field(..., description="Agent version")
    created_at: datetime = Field(..., description="Creation timestamp")
    template_source: Optional[TemplateSource] = Field(
        ..., description="Template source details"
    )
    agent_architecture: AgentArchitecture = Field(
        ..., description="Agent architecture details"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )


class AgentInputArgs(BaseModel):
    """Request model for agent execution"""

    input_args: List[Any] = Field(
        default={}, description="Input data for agent invocation"
    )
    input_kwargs: Dict[str, Any] = Field(
        default={}, description="Input data for agent invocation"
    )


class WebSocketActionType(str, Enum):
    START_STREAM = "start_stream"
    STOP_STREAM = "stop_stream"
    PING = "ping"


class WebSocketAgentRequest(BaseModel):
    """WebSocket request model for agent streaming"""
    action: WebSocketActionType
    agent_id: str
    input_data: AgentInputArgs
    stream_config: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Pydantic Models
class AgentRunRequest(BaseModel):
    """Request model for agent execution"""

    input_data: AgentInputArgs = Field(
        default={}, description="Input data for agent invocation"
    )


class AgentRunResponse(BaseModel):
    """Response model for agent execution"""

    success: bool
    output_data: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    agent_id: str


class CapacityInfo(BaseModel):
    """Database capacity information"""

    current_count: int
    max_capacity: int
    remaining_slots: int
    is_full: bool
    agents: List[Dict[str, Any]]


class AgentInfo(BaseModel):
    """Agent information and endpoints"""

    message: str
    version: str
    host: str
    port: int
    config: Dict[str, Any]
    endpoints: Dict[str, str]


# Message types for different agentic framework responses
class MessageType(Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_THOUGHT = "agent_thought"
    FINAL_RESPONSE = "final_response"
    ERROR = "error"
    STATUS = "status"
    RAW_DATA = "raw_data"
    STRUCTURED_DATA = "structured_data"


class SafeMessage(BaseModel):
    """Safe message wrapper for WebSocket communication"""
    id: str
    type: MessageType
    timestamp: str
    data: Any
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error
        }