# Pydantic schema for runagent.config.json
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TemplateSource(BaseModel):
    """Template source configuration"""

    repo_url: str = Field(..., description="GitHub repository URL")
    author: str = Field(..., description="Template Author name")
    path: str = Field(..., description="Path to template in repository")


class EntryPoint(BaseModel):
    """Entrypoint configuration"""

    file: str = Field(..., description="Entrypoint file")
    module: str = Field(..., description="Entrypoint module name")
    type: str = Field(..., description="Entrypoint type")


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
