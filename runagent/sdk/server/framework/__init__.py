from pathlib import Path
from typing import Dict

from runagent.sdk.server.framework.langgraph import LangGraphExecutor
from runagent.sdk.server.framework.langchain import LangChainExecutor
from runagent.sdk.server.framework.openai import OpenAIExecutor
from runagent.sdk.server.framework.generic import GenericExecutor
from runagent.sdk.server.framework.agno import AgnoExecutor
from runagent.sdk.server.framework.llamaindex import LlamaIndexExecutor
from runagent.sdk.server.framework.autogen import AutogenExecutor
from runagent.sdk.server.framework.crewai import CrewAIExecutor
from runagent.sdk.server.framework.ag2 import AG2Executor
from runagent.utils.schema import EntryPoint


def get_executor(
    agent_dir: Path, framework: str, agent_entrypoints: Dict[str, EntryPoint]
):
    executor_dict = {
        "default": GenericExecutor,
        "openai": OpenAIExecutor,
        "ag2": AG2Executor,
        "agno": AgnoExecutor,
        "autogen": AutogenExecutor,
        "crewai": CrewAIExecutor,
        "langgraph": LangGraphExecutor,
        "langchain": GenericExecutor,
        "letta": GenericExecutor,
        "llamaindex": LlamaIndexExecutor,
    }
    framework_executor = executor_dict.get(framework)
    if framework_executor is None:
        raise ValueError(f"Framework {framework} not supported yet.")
    return framework_executor(agent_dir)

