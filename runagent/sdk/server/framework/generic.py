from runagent.utils.schema import RunAgentConfig
from runagent.utils.imports import PackageImporter
from pathlib import Path
from typing import Dict
from runagent.utils.schema import EntryPoint


class GenericExecutor:
    def __init__(self, agent_dir: Path, agent_entrypoints: Dict[str, EntryPoint]):
        self.agent_dir = agent_dir
        self.agent_entrypoints = agent_entrypoints

        self.importer = PackageImporter(verbose=False)

        self._generic_entrypoint = None

        if "generic" in self.agent_entrypoints:
            ep = self.agent_entrypoints["generic"]
            self._generic_entrypoint = self.importer.resolve_import(
                self.agent_dir / ep.file, ep.module
            )

    def generic(self, *input_args, **input_kwargs):
        if self._generic_entrypoint is None:
            raise ValueError("No `generic` entrypoint found in agent config")
        return self._generic_entrypoint(*input_args, **input_kwargs)
