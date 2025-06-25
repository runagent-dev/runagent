from runagent.sdk.server.framework.langgraph import LangGraphExecutor
from runagent.utils.schema import EntryPoint
from pathlib import Path
from typing import Dict


def get_executor(
    agent_dir: Path, framework: str, agent_entrypoints: Dict[str, EntryPoint]
):
    if "generic" not in agent_entrypoints:
        raise ValueError("User has not exposed a generic entrypoint for agent")

    if framework == "langgraph":
        return LangGraphExecutor(agent_dir, agent_entrypoints)
    else:
        raise ValueError(f"Framework {framework} not supported yet.")
