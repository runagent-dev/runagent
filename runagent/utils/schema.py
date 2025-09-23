# Pydantic schema for runagent.config.json
from datetime import datetime
import typing as t
# from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from runagent.utils.enums.framework import Framework    


class TemplateSource(BaseModel):
    """Template source configuration"""

    repo_url: str = Field(..., description="GitHub repository URL")
    author: str = Field(..., description="Template Author name")
    path: str = Field(..., description="Path to template in repository")


class PythonicEntryPoint(BaseModel):
    """Configuration for a Python-based entrypoint."""

    file: str = Field(..., description="Path to the Python file containing the entrypoint")
    module: str = Field(..., description="Python module name for the entrypoint")
    tag: str = Field(..., description="Unique tag identifying this entrypoint")
    extractor: t.Optional[t.Dict[str, str]] = Field(
        default={},
        description="Optional mapping of output fields to JSONPath expressions for extracting data from the response"
    )


class WebHookEntryPoint(BaseModel):
    """Configuration for a webhook-based entrypoint."""

    webhook_url: str = Field(..., description="Webhook URL for the entrypoint")
    method: str = Field(..., description="HTTP method to use for the webhook")
    tag: str = Field(..., description="Entrypoint tag")
    timeout: int = Field(30, description="Timeout in seconds for the webhook request")
    extractor: t.Optional[t.Dict[str, str]] = Field(
        default={},
        description="JSONPath expression to extract data from the response"
    )


class AgentArchitecture(BaseModel):
    """Agent architecture configuration"""

    entrypoints: t.Union[
        t.List[PythonicEntryPoint], t.List[WebHookEntryPoint]
    ] = Field(
        ..., description="List of entrypoints"
    )

    @validator('entrypoints')
    def validate_unique_tags(cls, v):
        """Validate that all entrypoint tags are unique"""
        tags = [entrypoint.tag for entrypoint in v]
        if len(tags) != len(set(tags)):
            raise ValueError("All entrypoint tags must be unique")
        return v

from pydantic import ConfigDict


class RunAgentConfig(BaseModel):
    """Schema for runagent.config.json"""
    # model_config = ConfigDict(
    #     use_enum_values=True,  # Automatically convert enums to values
    #     json_encoders={
    #         datetime: lambda v: v.isoformat()  # Custom datetime serialization
    #     }
    # )

    agent_name: str = Field(..., description="Name of the agent")
    description: str = Field(..., description="Description of the agent")
    framework: Framework = Field(..., description="Framework used (langchain, etc)")
    template: str = Field(..., description="Template name")
    version: str = Field(..., description="Agent version")
    created_at: datetime = Field(..., description="Creation timestamp")
    template_source: t.Optional[TemplateSource] = Field(
        ..., description="Template source details"
    )
    agent_architecture: AgentArchitecture = Field(
        ..., description="Agent architecture details"
    )
    env_vars: t.Optional[t.Dict[str, str]] = Field(
        default_factory=dict, description="Environment variables"
    )

    def to_dict(self) -> dict:
        """Convert to dictionary with custom serialization"""
        data = self.model_dump()
        
        # Convert enum to string value
        if isinstance(data.get('framework'), Framework):
            data['framework'] = data['framework'].value
            
        # Convert datetime to ISO string if needed
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
            
        return data

class AgentInputArgs(BaseModel):
    """Request model for agent execution"""

    input_args: t.List[t.Any] = Field(
        default={}, description="Input data for agent invocation"
    )
    input_kwargs: t.Dict[str, t.Any] = Field(
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
    stream_config: t.Optional[t.Dict[str, t.Any]] = Field(default_factory=dict)


# Pydantic Models
class AgentRunRequest(BaseModel):
    """Request model for agent execution"""

    input_data: AgentInputArgs = Field(
        default={}, description="Input data for agent invocation"
    )


class AgentRunResponse(BaseModel):
    """Response model for agent execution"""

    success: bool
    output_data: t.Optional[t.Any] = None
    error: t.Optional[str] = None
    execution_time: t.Optional[float] = None
    agent_id: str


class CapacityInfo(BaseModel):
    """Database capacity information"""

    current_count: int
    max_capacity: int
    remaining_slots: int
    is_full: bool
    agents: t.List[t.Dict[str, t.Any]]


class AgentInfo(BaseModel):
    """Agent information and endpoints"""

    message: str
    version: str
    host: str
    port: int
    config: t.Dict[str, t.Any]
    endpoints: t.Dict[str, str]


# Message types for different agentic framework responses
class MessageType(Enum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_THOUGHT = "agent_thought"
    FINAL_RESPONSE = "final_response"
    ERROR = "error"
    DATA = "data"
    STATUS = "status"
    RAW_DATA = "raw_data"
    STRUCTURED_DATA = "structured_data"


class SafeMessage(BaseModel):
    """Safe message wrapper for WebSocket communication"""
    id: str
    type: MessageType
    timestamp: str
    data: t.Any
    metadata: t.Optional[t.Dict[str, t.Any]] = None
    error: t.Optional[str] = None

    def to_dict(self) -> t.Dict[str, t.Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error
        }
