from pathlib import Path
from typing import Dict

from runagent.sdk.server.framework.langgraph import LangGraphExecutor
from runagent.sdk.server.framework.generic import GenericExecutor

from runagent.utils.schema import EntryPoint, EntryPointType


def get_executor(
    agent_dir: Path, framework: str, agent_entrypoints: Dict[str, EntryPoint]
):
    # Check if any valid entrypoint type exists
    valid_entrypoint_found = False
    for entrypoint_type in EntryPointType:
        if entrypoint_type in agent_entrypoints:
            valid_entrypoint_found = True
            break
    if not valid_entrypoint_found:
        raise ValueError(f"No valid entrypoint type found in agent configuration. Valid types are: {[t.value for t in EntrypointType]}")

    if framework == "langgraph":
        return LangGraphExecutor(agent_dir, agent_entrypoints)
    elif framework in ["langchain", "llamaindex", "crewai", "autogen"]:
        # Use generic executor for other frameworks
        return GenericExecutor(agent_dir, agent_entrypoints)
    else:
        raise ValueError(f"Framework {framework} not supported yet.")