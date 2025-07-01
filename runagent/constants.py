import os
from enum import Enum
from pathlib import Path

# Template Repository Configuration
TEMPLATE_REPO_URL = os.getenv(
    "RUNAGENT_TEMPLATE_REPO", "https://github.com/runagent-dev/runagent.git"
)
TEMPLATE_BRANCH = os.getenv("RUNAGENT_TEMPLATE_BRANCH", "main")
TEMPLATE_PREPATH = os.getenv("RUNAGENT_TEMPLATE_PREPATH", "templates")

# Default Template Settings
DEFAULT_FRAMEWORK = "langchain"
DEFAULT_TEMPLATE = "basic"

# Environment Variables
ENV_RUNAGENT_API_KEY = "RUNAGENT_API_KEY"
# ENV_RUNAGENT_BASE_URL = "http://20.244.107.179:8330/"
ENV_RUNAGENT_BASE_URL = "http://52.237.88.147:8330/"
ENV_LOCAL_CACHE_DIRECTORY = "RUNAGENT_CACHE_DIR"
ENV_RUNAGENT_LOGGING_LEVEL = "RUNAGENT_LOGGING_LEVEL"

# Local Configuration
LOCAL_CACHE_DIRECTORY_PATH = "~/.runagent"
USER_DATA_FILE_NAME = "user_data.json"
DEFAULT_BASE_URL = "http://52.237.88.147:8330/"
# DEFAULT_BASE_URL = "http://52.237.88.147:8330/"
AGENT_CONFIG_FILE_NAME = "runagent.config.json"

# Setup cache directory
_cache_dir = os.environ.get(ENV_LOCAL_CACHE_DIRECTORY)
LOCAL_CACHE_DIRECTORY = str(
    Path(_cache_dir)
    if _cache_dir is not None
    else Path(LOCAL_CACHE_DIRECTORY_PATH).expanduser()
)

try:
    Path(LOCAL_CACHE_DIRECTORY).mkdir(parents=True, exist_ok=True)
except OSError as e:
    raise RuntimeError(
        f"Cache directory {LOCAL_CACHE_DIRECTORY} is not writable please "
        f"provide a path that is writable using {ENV_LOCAL_CACHE_DIRECTORY} "
        "environment variable."
    ) from e


# Framework Enums
class Framework(str, Enum):
    LANGGRAPH = "langgraph"
    LANGCHAIN = "langchain"
    LLAMAINDEX = "llamaindex"
    CREWAI = "crewai"
    AUTOGEN = "autogen"


class TemplateVariant(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
