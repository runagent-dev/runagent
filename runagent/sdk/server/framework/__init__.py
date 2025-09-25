from pathlib import Path
# from typing import Dict
import typing as t
from runagent.utils.enums.framework import Framework
from runagent.sdk.server.framework.langgraph import LangGraphExecutor
from runagent.sdk.server.framework.langchain import LangChainExecutor
from runagent.sdk.server.framework.openai import OpenAIExecutor
from runagent.sdk.server.framework.generic import GenericExecutor
from runagent.sdk.server.framework.agno import AgnoExecutor
from runagent.sdk.server.framework.llamaindex import LlamaIndexExecutor
from runagent.sdk.server.framework.autogen import AutogenExecutor
from runagent.sdk.server.framework.crewai import CrewAIExecutor
from runagent.sdk.server.framework.ag2 import AG2Executor
from runagent.sdk.server.framework.n8n import N8NExecutor
from runagent.sdk.server.framework.parlant import ParlantExecutor
from runagent.utils.schema import PythonicEntryPoint, WebHookEntryPoint


def get_executor(
    agent_dir: Path, framework: Framework, agent_entrypoints: t.Dict[str, t.Union[PythonicEntryPoint, WebHookEntryPoint]]
):
    executor_dict = {
        Framework.DEFAULT: GenericExecutor,
        Framework.OPENAI: OpenAIExecutor,
        Framework.AG2: AG2Executor,
        Framework.AGNO: AgnoExecutor,
        Framework.AUTOGEN: AutogenExecutor,
        Framework.CREWAI: CrewAIExecutor,
        Framework.LANGGRAPH: LangGraphExecutor,
        Framework.LANGCHAIN: GenericExecutor,
        Framework.LETTA: GenericExecutor,
        Framework.LLAMAINDEX: LlamaIndexExecutor,
        Framework.N8N: N8NExecutor
    }
    framework_executor = executor_dict.get(framework)
    if framework_executor is None:
        raise ValueError(f"Framework {framework} not supported yet.")
    return framework_executor(agent_dir)

