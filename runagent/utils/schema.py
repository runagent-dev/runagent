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
    template_source: TemplateSource = Field(
        ..., description="Template source details"
    )
    agent_architecture: t.Optional[AgentArchitecture] = Field(
        default=None, description="Agent architecture details"
    )
    env_vars: t.Optional[t.Dict[str, str]] = Field(
        default_factory=dict, description="Environment variables"
    )
    
    # NEW FIELDS - Agent ID management
    agent_id: str = Field(..., description="Unique agent identifier")
    
    # Authentication settings
    auth_settings: t.Optional[t.Dict[str, t.Any]] = Field(
        default_factory=lambda: {"type": "none"}, 
        description="Authentication configuration"
    )

    def to_dict(self) -> dict:
        """Convert to dictionary with custom serialization"""
        # Use model_dump with exclude_none=False to include all fields
        # Use exclude_unset=False to include all fields (even defaults)
        data = self.model_dump(exclude_none=False, exclude_unset=False)
        
        # Convert enum to string value
        if isinstance(data.get('framework'), Framework):
            data['framework'] = data['framework'].value
            
        # Convert datetime to ISO string if needed
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        # Convert AgentArchitecture to dict if present
        if isinstance(data.get('agent_architecture'), AgentArchitecture):
            arch = data['agent_architecture']
            data['agent_architecture'] = {
                'entrypoints': [ep.model_dump() if hasattr(ep, 'model_dump') else ep.dict() if hasattr(ep, 'dict') else ep for ep in arch.entrypoints]
            }
        
        # Convert TemplateSource to dict if present
        if isinstance(data.get('template_source'), TemplateSource):
            ts = data['template_source']
            data['template_source'] = ts.model_dump() if hasattr(ts, 'model_dump') else ts.dict()
        
        # Remove None values for optional fields (but keep empty lists/dicts)
        cleaned_data = {}
        for key, value in data.items():
            if value is not None:
                cleaned_data[key] = value
        
        return cleaned_data
    
    def model_dump_json(self, **kwargs) -> str:
        """Convert to JSON string with proper serialization"""
        import json
        return json.dumps(self.to_dict(), indent=2, **kwargs)


class WebSocketActionType(str, Enum):
    START_STREAM = "start_stream"
    STOP_STREAM = "stop_stream"
    PING = "ping"


class WebSocketAgentRequest(BaseModel):
    """WebSocket request model for agent streaming"""
    action: WebSocketActionType
    entrypoint_tag: str = Field(..., description="Entrypoint tag")
    input_args: t.List[t.Any] = Field(
        default_factory=list, description="Input data for positional arguments"
    )
    input_kwargs: t.Dict[str, t.Any] = Field(
        default_factory=dict, description="Input data for keyword arguments"
    )
    stream_config: t.Optional[t.Dict[str, t.Any]] = Field(default_factory=dict)


# Pydantic Models
class AgentRunRequest(BaseModel):
    """Request model for agent execution"""
    entrypoint_tag: str = Field(..., description="Entrypoint tag")
    input_args: t.List[t.Any] = Field(
        default_factory=list, description="Input data for positional arguments"
    )
    input_kwargs: t.Dict[str, t.Any] = Field(
        default_factory=dict, description="Input data for keyword arguments"
    )



class AgentRunResponse(BaseModel):
    """Response model for agent execution"""

    success: bool
    output_data: t.Optional[t.Any] = None
    error: t.Optional[str] = None
    execution_time: t.Optional[float] = None
    agent_id: str


class ExecutionData(BaseModel):
    """Execution data for the new response format"""
    
    execution_id: str
    agent_id: str
    user_id: t.Optional[str] = None
    deployment_id: t.Optional[str] = None
    entrypoint_id: t.Optional[str] = None
    status: str
    started_at: str
    completed_at: t.Optional[str] = None
    runtime_seconds: t.Optional[float] = None
    input_data: t.Dict[str, t.Any]
    result_data: t.Optional[t.Dict[str, t.Any]] = None
    execution_metadata: t.Optional[t.Dict[str, t.Any]] = None
    error_message: t.Optional[str] = None
    is_local: bool = True
    agent_name: t.Optional[str] = None
    project_id: t.Optional[str] = None
    project_name: t.Optional[str] = None
    endpoint: t.Optional[str] = None
    priority: str = "normal"
    success: bool
    result: t.Optional[t.Dict[str, t.Any]] = None
    error: t.Optional[str] = None


class ErrorDetail(BaseModel):
    """Error detail structure for API responses"""
    
    code: str
    message: str
    details: t.Optional[t.Any] = None
    field: t.Optional[str] = None


class AgentRunResponseV2(BaseModel):
    """New response model for agent execution with detailed execution data"""
    
    success: bool
    data: t.Optional[ExecutionData] = None
    message: t.Optional[str] = None
    error: t.Optional[ErrorDetail] = None
    timestamp: str
    request_id: str


class AgentRunResponseMinimal(BaseModel):
    """Simplified response model for agent execution returning structured output"""

    success: bool
    data: t.Optional[str] = None
    message: t.Optional[str] = None
    error: t.Optional[ErrorDetail] = None
    timestamp: str
    request_id: str


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
