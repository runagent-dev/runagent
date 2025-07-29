from enum import Enum
import typing as t


class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class PythonicType(Enum):
    AG2 = "ag2"
    AGNO = "agno"
    AUTOGEN = "autogen"
    CREWAI = "crewai"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    LETTA = "letta"
    LLAMAINDEX = "llamaindex"
    OPENAI = "openai"


class WebhookType(Enum):
    N8N = "n8n"


FrameworkType = t.Union[PythonicType, WebhookType]
