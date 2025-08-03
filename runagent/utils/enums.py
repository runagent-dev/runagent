from enum import Enum

class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class Framework(Enum):
    # Default option
    DEFAULT = "default"

    # Pythonic frameworks
    AG2 = "ag2"
    AGNO = "agno"
    AUTOGEN = "autogen"
    CREWAI = "crewai"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    LETTA = "letta"
    LLAMAINDEX = "llamaindex"
    OPENAI = "openai"

    # Webhook frameworks
    N8N = "n8n"

    @classmethod
    def get_pythonic(cls):
        """Get all Python-based frameworks"""
        return [
            cls.AG2, cls.AGNO, cls.AUTOGEN,
            cls.CREWAI, cls.LANGCHAIN, cls.LANGGRAPH,
            cls.LETTA, cls.LLAMAINDEX, cls.OPENAI
        ]
        
    @classmethod
    def get_webhook(cls):
        """Get all webhook-based frameworks"""
        return [cls.N8N]

    @classmethod
    def get_selectable_frameworks(cls):
        """Get frameworks that can be selected (excludes DEFAULT)"""
        return [fw for fw in cls if fw != cls.DEFAULT]

    @classmethod
    def from_value(cls, value: str):
        """Get framework enum from string value"""
        for fw in cls:
            if fw.value == value:
                return fw
        return None

    def is_pythonic(self):
        """Check if this framework is Python-based"""
        return self in self.get_pythonic()
    
    def is_webhook(self):
        """Check if this framework is webhook-based"""
        return self in self.get_webhook()