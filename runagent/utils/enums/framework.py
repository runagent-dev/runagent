from enum import Enum
import typing as t


# Framework Enum with efficient caching
class Framework(Enum):
    DEFAULT = "default"
    AG2 = "ag2"
    AGNO = "agno"
    AUTOGEN = "autogen"
    CREWAI = "crewai"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    LETTA = "letta"
    LLAMAINDEX = "llamaindex"
    OPENAI = "openai"
    N8N = "n8n"

    @classmethod
    def _pythonic_frameworks_cache(cls) -> t.FrozenSet['Framework']:
        return frozenset({
                cls.AG2, cls.AGNO, cls.AUTOGEN, cls.CREWAI,
                cls.LANGCHAIN, cls.LANGGRAPH, cls.LETTA,
                cls.LLAMAINDEX, cls.OPENAI
            })

    @classmethod
    def _webhook_frameworks_cache(cls) -> t.FrozenSet['Framework']:
        return frozenset({cls.N8N})
        
    @classmethod
    def get_pythonic_frameworks(cls) -> t.FrozenSet['Framework']:
        """Get all pythonic frameworks (cached)"""
        return cls._pythonic_frameworks_cache()

    @classmethod
    def get_webhook_frameworks(cls) -> t.FrozenSet['Framework']:
        """Get all webhook frameworks (cached)"""
        return cls._webhook_frameworks_cache()

    @classmethod
    def get_selectable_frameworks(cls) -> t.List['Framework']:
        """Get frameworks that can be selected (excluding DEFAULT)"""
        return [f for f in cls if f != cls.DEFAULT]

    @classmethod
    def from_string(cls, value: str) -> 'Framework':
        """Convert string to Framework with validation"""
        try:
            return cls(value)
        except ValueError:
            valid_values = [f.value for f in cls]
            raise ValueError(f"Invalid framework: '{value}'. Valid options: {valid_values}")

    @classmethod
    def validate_framework_str(cls, value: str) -> bool:
        """Check if string is a valid framework"""
        try:
            cls(value)
            return True
        except ValueError:
            return False

    def is_pythonic(self) -> bool:
        """Check if this framework is pythonic"""
        return self in self.get_pythonic_frameworks()

    def is_webhook(self) -> bool:
        """Check if this framework is webhook"""
        return self in self.get_webhook_frameworks()

    def is_default(self) -> bool:
        """Check if this framework is the default"""
        return self == self.DEFAULT

    @property
    def category(self) -> str:
        """Get the category of this framework"""
        if self.is_default():
            return "default"
        elif self.is_pythonic():
            return "pythonic"
        elif self.is_webhook():
            return "webhook"
        else:
            return "unknown"
    # Class methods for string validation and conversion
    @classmethod
    def from_string(cls, framework_str: str) -> 'Framework':
        """Convert string to Framework enum with validation"""
        try:
            return cls(framework_str)
        except ValueError:
            valid_frameworks = [f.value for f in cls]
            raise ValueError(f"Invalid framework: '{framework_str}'. Valid options: {valid_frameworks}")

    @classmethod
    def is_valid_framework_string(cls, framework_str: str) -> bool:
        """Check if string is a valid framework"""
        try:
            cls(framework_str)
            return True
        except ValueError:
            return False

    # @classmethod
    # def is_pythonic_string(cls, framework_str: str) -> bool:
    #     """Check if string represents a pythonic framework"""
    #     try:
    #         framework = cls(framework_str)
    #         return framework.is_pythonic()
    #     except ValueError:
    #         return False

    # @classmethod
    # def is_webhook_string(cls, framework_str: str) -> bool:
    #     """Check if string represents a webhook framework"""
    #     try:
    #         framework = cls(framework_str)
    #         return framework.is_webhook()
    #     except ValueError:
    #         return False

    # @classmethod
    # def is_default_string(cls, framework_str: str) -> bool:
    #     """Check if string represents the default framework"""
    #     try:
    #         framework = cls(framework_str)
    #         return framework.is_default()
    #     except ValueError:
    #         return False

    @classmethod
    def from_str(cls, framework_str: str) -> str:
        """Get category from string"""
        try:
            framework = cls(framework_str)
            return framework.category
        except ValueError:
            return "invalid"

    # # Utility class methods
    # @classmethod
    # def get_all_framework_values(cls) -> t.List[str]:
    #     """Get all framework values as strings"""
    #     return [f.value for f in cls]

    # @classmethod
    # def get_pythonic_framework_values(cls) -> t.List[str]:
    #     """Get pythonic framework values as strings"""
    #     return [f.value for f in cls.get_pythonic_frameworks()]

    # @classmethod
    # def get_webhook_framework_values(cls) -> t.List[str]:
    #     """Get webhook framework values as strings"""
    #     return [f.value for f in cls.get_webhook_frameworks()]
