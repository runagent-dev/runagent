import asyncio
import inspect
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from runagent.utils.imports import PackageImporter
from runagent.utils.schema import PythonicEntryPoint, RunAgentConfig
from runagent.utils.serializer import CoreSerializer
from runagent.utils.response import extract_jsonpath, to_dict
from runagent.utils.logging_utils import is_verbose_logging_enabled

console = Console()


class GenericExecutor:

    rerserved_tags = list()

    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir
        self.importer = PackageImporter(verbose=False)

    def get_runner(self, entrypoint: PythonicEntryPoint):
        """
        Always returns an async function, regardless of whether the 
        underlying entrypoint is sync or async.
        """
        resolved_entrypoint = self._entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / entrypoint.file,
            entrypoint_module=entrypoint.module,
        )
        
        async def normalized_runner(*input_args, **input_kwargs):
            if is_verbose_logging_enabled():
                console.print(f"🔍 [cyan]Entrypoint:[/cyan] {entrypoint.tag}")
                console.print(f"🔍 [cyan]Input data:[/cyan] *{input_args}, **{input_kwargs}")
            
            if inspect.iscoroutinefunction(resolved_entrypoint):
                if is_verbose_logging_enabled():
                    print("resolved async", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
                result = await resolved_entrypoint(*input_args, **input_kwargs)
            else:
                if is_verbose_logging_enabled():
                    print("resolved sync (wrapped in async)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
                # Run sync function in executor to avoid blocking
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: resolved_entrypoint(*input_args, **input_kwargs)
                )
            
            if entrypoint.extractor:
                result = extract_jsonpath(result, entrypoint.extractor)
            
            return result
        
        return normalized_runner

    def get_stream_runner(self, entrypoint: PythonicEntryPoint):
        """
        Always returns an async generator, regardless of whether the 
        underlying entrypoint is sync or async.
        """
        resolved_entrypoint = self._entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / entrypoint.file,
            entrypoint_module=entrypoint.module,
        )

        async def normalized_stream_runner(*input_args, **input_kwargs):
            if is_verbose_logging_enabled():
                console.print(f"🔍 [cyan]Entrypoint:[/cyan] {entrypoint.tag}")
                console.print(f"🔍 [cyan]Input data:[/cyan] *{input_args}, **{input_kwargs}")
            
            if inspect.isasyncgenfunction(resolved_entrypoint):
                # Native async generator
                if is_verbose_logging_enabled():
                    print("resolved async generator", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
                async for chunk in resolved_entrypoint(*input_args, **input_kwargs):
                    if entrypoint.extractor:
                        chunk = extract_jsonpath(chunk, entrypoint.extractor)
                    yield chunk
                    await asyncio.sleep(0)
            
            elif inspect.iscoroutinefunction(resolved_entrypoint):
                # Async function that returns iterable
                if is_verbose_logging_enabled():
                    print("resolved async function (returns iterable)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
                result = await resolved_entrypoint(*input_args, **input_kwargs)
                for chunk in result:
                    if entrypoint.extractor:
                        chunk = extract_jsonpath(chunk, entrypoint.extractor)
                    yield chunk
                    await asyncio.sleep(0)
            
            elif inspect.isgeneratorfunction(resolved_entrypoint):
                # Sync generator - consume in executor
                if is_verbose_logging_enabled():
                    print("resolved sync generator (wrapped in async)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
                generator = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: resolved_entrypoint(*input_args, **input_kwargs)
                )
                for chunk in generator:
                    if entrypoint.extractor:
                        chunk = extract_jsonpath(chunk, entrypoint.extractor)
                    yield chunk
                    await asyncio.sleep(0)
            
            else:
                # Sync function that returns iterable
                print("resolved sync function (returns iterable, wrapped in async)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: resolved_entrypoint(*input_args, **input_kwargs)
                )
                for chunk in result:
                    if entrypoint.extractor:
                        chunk = extract_jsonpath(chunk, entrypoint.extractor)
                    yield chunk
                    await asyncio.sleep(0)

        return normalized_stream_runner

    def _entrypoint_resolver(self, entrypoint_filepath: Path, entrypoint_module: str):
        verbose = is_verbose_logging_enabled()
        if verbose:
            print(f"DEBUG: Resolving entrypoint - filepath: {entrypoint_filepath}, module: {entrypoint_module}")
        primary_module, secondary_attr = (
            entrypoint_module.split(".", 1) + [""]
        )[:2]
        if verbose:
            print(f"DEBUG: Split module - primary: {primary_module}, secondary: {secondary_attr}")
        
        resolved_module = self.importer.resolve_import(
                entrypoint_filepath, primary_module
            )
        if verbose:
            print(f"DEBUG: Resolved primary module: {resolved_module}")
        
        if secondary_attr:
            attrs = secondary_attr.split('.')
            if verbose:
                print(f"DEBUG: Secondary attributes to resolve: {attrs}")
            for attr in attrs:
                resolved_module = getattr(resolved_module, attr)
                if verbose:
                    print(f"DEBUG: Resolved attribute {attr}: {resolved_module}")

        if verbose:
            print(f"DEBUG: Final resolved module: {resolved_module}")
            print("Resolving", (entrypoint_module, resolved_module))
        return resolved_module

    def _get_function_type(self, func):
        """
        Determine the type of function for debugging purposes.
        Returns: str describing the function type
        """
        if inspect.isasyncgenfunction(func):
            return "async_generator"
        elif inspect.iscoroutinefunction(func):
            return "async_function"
        elif inspect.isgeneratorfunction(func):
            return "sync_generator"
        else:
            return "sync_function"