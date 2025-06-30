from pathlib import Path
from typing import Dict

from runagent.sdk.server.framework.generic import GenericExecutor
from runagent.utils.schema import EntryPoint


class LangChainExecutor(GenericExecutor):
    def __init__(self, agent_dir: Path, agent_entrypoints: Dict[str, EntryPoint]):
        super().__init__(agent_dir, agent_entrypoints)

        self._invoke_entrypoint = None
        self._stream_entrypoint = None
        self._stream_token_entrypoint = None

        if "invoke" in agent_entrypoints:
            ep = agent_entrypoints["invoke"]
            self._invoke_entrypoint = self.importer.resolve_import(
                self.agent_dir / ep.file, ep.module
            )
        if "stream" in agent_entrypoints:
            ep = agent_entrypoints["stream"]
            self._stream_entrypoint = self.importer.resolve_import(
                self.agent_dir / ep.file, ep.module
            )
        if "stream_token" in agent_entrypoints:
            ep = agent_entrypoints["stream_token"]
            self._stream_token_entrypoint = self.importer.resolve_import(
                self.agent_dir / ep.file, ep.module
            )

    def invoke(self, *input_args, **input_kwargs):
        if self._invoke_entrypoint is None:
            raise ValueError("No `invoke` entrypoint found in agent config")
        return self._invoke_entrypoint.invoke(*input_args, **input_kwargs)

    def stream(self, *input_args, **input_kwargs):
        if self._stream_entrypoint is None:
            raise ValueError("No `stream` entrypoint found in agent config")
        return self._stream_entrypoint(*input_args, **input_kwargs)

    def stream_token(self, *input_args, **input_kwargs):
        if self._stream_token_entrypoint is None:
            raise ValueError("No `stream_token` entrypoint found in agent config")
        return self._stream_token_entrypoint(*input_args, **input_kwargs)
