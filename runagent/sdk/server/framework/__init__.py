from pathlib import Path
from typing import Dict

from runagent.sdk.server.framework.langgraph import LangGraphExecutor
from runagent.sdk.server.framework.langchain import LangChainExecutor
from runagent.sdk.server.framework.generic import GenericExecutor
from runagent.utils.schema import EntryPoint


def get_executor(
    agent_dir: Path, framework: str, agent_entrypoints: Dict[str, EntryPoint]
):
    if framework == "langgraph":
        return LangGraphExecutor(agent_dir)
    elif framework == "langchain":
        return GenericExecutor(agent_dir)
    elif framework == "letta":
        return GenericExecutor(agent_dir)
    elif framework == "default":
        return GenericExecutor(agent_dir)
    else:
        raise ValueError(f"Framework {framework} not supported yet.")
