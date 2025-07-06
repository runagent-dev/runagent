import asyncio
from pathlib import Path
from typing import Dict, List

from runagent.utils.imports import PackageImporter
from runagent.utils.schema import EntryPoint, RunAgentConfig
from runagent.utils.serializer import CoreSerializer


class GenericExecutor:

    rerserved_tags = list()

    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir

        self.importer = PackageImporter(verbose=False)

    def get_runner(self, entrypoint: EntryPoint):
        
        resolved_entrypoint = self._entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / entrypoint.file,
            entrypoint_module=entrypoint.module,
        )
        
        def generic_runner(*input_args, **input_kwargs):
            print("resolved non stream", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
            result = resolved_entrypoint(*input_args, **input_kwargs)
            return result
        return generic_runner

    def get_stream_runner(self, entrypoint: EntryPoint):
        
        resolved_entrypoint = self._entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / entrypoint.file,
            entrypoint_module=entrypoint.module,
        )

        async def generic_stream_runner(*input_args, **input_kwargs):
            for chunk in resolved_entrypoint(
                *input_args,
                **input_kwargs
            ):
                yield chunk
                await asyncio.sleep(0)

        return generic_stream_runner

    def _entrypoint_resolver(self, entrypoint_filepath: Path, entrypoint_module: str):
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
        print("Resolving", (entrypoint_module, resolved_module))
        return resolved_module


    # def run(self, *input_args, **input_kwargs):
    #     if self._generic_entrypoint is None:
    #         raise ValueError("No `generic` entrypoint found in agent config")
    #     result_obj = self._generic_entrypoint(*input_args, **input_kwargs)
    #     result_json = self.serializer.serialize_object(result_obj)
    #     return result_json

    # async def run_stream(self, *input_args, **input_kwargs):
    #     if self._generic_stream_entrypoint is None:
    #         raise ValueError("No `generic_stream` entrypoint found in agent config")

    #     for chunk in self._generic_stream_entrypoint(
    #         *input_args,
    #         **input_kwargs
    #     ):
    #         yield chunk
    #         await asyncio.sleep(0)


    