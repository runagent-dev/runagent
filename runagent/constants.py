import os
from pathlib import Path
from enum import Enum

TEMPLATE_REPO_URL = os.getenv("RUNAGENT_TEMPLATE_REPO", "https://github.com/runagent-dev/runagent.git")
TEMPLATE_BRANCH = os.getenv("RUNAGENT_TEMPLATE_BRANCH", "main")
TEMPLATE_PREPATH = os.getenv("RUNAGENT_TEMPLATE_PREPATH", "templates")


ENV_RUNAGENT_API_KEY = "RUNAGENT_API_KEY"
ENV_RUNAGENT_BASE_URL = "RUNAGENT_BASE_URL"
ENV_LOCAL_CACHE_DIRECTORY = "RUNAGENT_CACHE_DIR"
ENV_RUNAGENT_LOGGING_LEVEL = "RUNAGENT_LOGGING_LEVEL"


LOCAL_CACHE_DIRECTORY_PATH = "~/.runagent"
USER_DATA_FILE_NAME = "user_data.json"
DEFAULT_BASE_URL = "http://localhost:8320/"

AGENT_CONFIG_FILE_NAME = "runagent.config.json"


_cache_dir = os.environ.get(ENV_LOCAL_CACHE_DIRECTORY)
LOCAL_CACHE_DIRECTORY = str(Path(_cache_dir) if _cache_dir is not None else Path(LOCAL_CACHE_DIRECTORY_PATH).expanduser())

try:
    Path(LOCAL_CACHE_DIRECTORY).mkdir(parents=True, exist_ok=True)
    # if not Path(LOCAL_CACHE_DIRECTORY).is_writable():
    #     raise OSError
except OSError as e:
    raise RuntimeError(
        f"Cache directory {LOCAL_CACHE_DIRECTORY} is not writable please "
        f"provide a path that is writable using {ENV_LOCAL_CACHE_DIRECTORY} "
        "environment variable."
    ) from e


class Framework(str, Enum):
    LANGGRAPH = "langgraph"
    LANGCHAIN = "langchain"
    LLAMAINDEX = "llamaindex"
    CREWAI = "crewai"
    AUTOGEN = "autogen"


class TemplateVariant(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"