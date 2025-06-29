import asyncio
from pathlib import Path
from typing import Dict

from runagent.utils.imports import PackageImporter
from runagent.utils.schema import EntryPoint, RunAgentConfig, EntryPointType
from runagent.utils.serializer import CoreSerializer


class GenericExecutor:
    def __init__(self, agent_dir: Path, agent_entrypoints: Dict[str, EntryPoint]):
        self.agent_dir = agent_dir
        self.agent_entrypoints = agent_entrypoints

        self.importer = PackageImporter(verbose=False)
        self.serializer = CoreSerializer(max_size_mb=5.0)

        generic_ep = self.agent_entrypoints.get(EntryPointType.GENERIC)
        generic_stream_ep = self.agent_entrypoints.get(EntryPointType.GENERIC_STREAM)

        self._generic_entrypoint = self.entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / generic_ep.file,
            entrypoint_module=generic_ep.module,
        ) if generic_ep else None

        self._generic_stream_entrypoint = self.entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / generic_stream_ep.file,
            entrypoint_module=generic_stream_ep.module,
        ) if generic_stream_ep else None

    def entrypoint_resolver(self, entrypoint_filepath: Path, entrypoint_module: str):
        print(f"DEBUG: Resolving entrypoint - filepath: {entrypoint_filepath}, module: {entrypoint_module}")
        primary_module, secondary_attr = (
            entrypoint_module.split(".", 1) + [""]
        )[:2]
        print(f"DEBUG: Split module - primary: {primary_module}, secondary: {secondary_attr}")
        
        resolved_module = self.importer.resolve_import(
                entrypoint_filepath, primary_module
            )
        print(f"DEBUG: Resolved primary module: {resolved_module}")
        
        if secondary_attr:
            attrs = secondary_attr.split('.')
            print(f"DEBUG: Secondary attributes to resolve: {attrs}")
            for attr in attrs:
                resolved_module = getattr(resolved_module, attr)
                print(f"DEBUG: Resolved attribute {attr}: {resolved_module}")

        print(f"DEBUG: Final resolved module: {resolved_module}")
        return resolved_module

    def generic(self, *input_args, **input_kwargs):
        if self._generic_entrypoint is None:
            raise ValueError("No `generic` entrypoint found in agent config")
        result_obj = self._generic_entrypoint(*input_args, **input_kwargs)
        result_json = self.serializer.serialize_object(result_obj)
        return result_json

    async def generic_stream(self, *input_args, **input_kwargs):
        if self._generic_stream_entrypoint is None:
            raise ValueError("No `generic_stream` entrypoint found in agent config")

        for chunk in self._generic_stream_entrypoint(
            *input_args,
            **input_kwargs
        ):
            yield chunk
            await asyncio.sleep(0)


    