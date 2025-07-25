import asyncio
import httpx
import inspect
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from runagent.utils.imports import PackageImporter
from runagent.utils.schema import EntryPoint, RunAgentConfig
from runagent.utils.serializer import CoreSerializer
from runagent.utils.response import extract_jsonpath, to_dict

console = Console()


class N8nExecutor:

    rerserved_tags = list()

    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir

    def get_runner(self, entrypoint: EntryPoint):
        """
        Always returns an async function, regardless of whether the 
        underlying entrypoint is sync or async.
        """
        resolved_entrypoint = self._entrypoint_resolver(
            entrypoint_filepath=self.agent_dir / entrypoint.file,
            entrypoint_module=entrypoint.module,
        )

        async def normalized_runner(*input_args, **input_kwargs):
            console.print(f"🔍 [cyan]Entrypoint:[/cyan] {entrypoint.tag}")
            console.print(f"🔍 [cyan]Input data:[/cyan] *{input_args}, **{input_kwargs}")

            # Check for invalid argument combinations
            if len(input_args) > 1:
                raise ValueError("Too many positional arguments. Expected at most 1.")
    
            if input_args and input_kwargs:
                raise ValueError("Cannot specify both positional and keyword arguments.")
    
            if len(input_kwargs) > 1 or (input_kwargs and 'payload' not in input_kwargs):
                raise ValueError("Only 'payload' keyword argument is allowed.")
    
            # Extract payload
            if input_args:
                # normalized_runner({...})
                payload = input_args[0]
            elif 'payload' in input_kwargs:
                # normalized_runner(payload={...})
                payload = input_kwargs['payload']
            else:
                # normalized_runner()
                payload = None
    
            async with httpx.AsyncClient() as client:
                if entrypoint.method == "post":
                    # POST request with JSON payload
                    response = await client.post(
                        entrypoint.webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                elif entrypoint.method == "get":
                    # GET request when no payload
                    response = await client.get(entrypoint.webhook_url)
        
                response.raise_for_status()  # Raise exception for HTTP errors
                result = response.json()

                if entrypoint.extractor:
                    result = extract_jsonpath(result, entrypoint.extractor)
                
                return result
                

            
        
        # async def normalized_runner(*input_args, **input_kwargs):
        #     console.print(f"🔍 [cyan]Entrypoint:[/cyan] {entrypoint.tag}")
        #     console.print(f"🔍 [cyan]Input data:[/cyan] *{input_args}, **{input_kwargs}")
            
        #     if inspect.iscoroutinefunction(resolved_entrypoint):
        #         print("resolved async", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
        #         result = await resolved_entrypoint(*input_args, **input_kwargs)
        #     else:
        #         print("resolved sync (wrapped in async)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
        #         # Run sync function in executor to avoid blocking
        #         result = await asyncio.get_event_loop().run_in_executor(
        #             None, lambda: resolved_entrypoint(*input_args, **input_kwargs)
        #         )
            
        #     if entrypoint.extractor:
        #         result = extract_jsonpath(result, entrypoint.extractor)
            
        #     return result
        
        # return normalized_runner

    # def get_stream_runner(self, entrypoint: EntryPoint):
    #     """
    #     Always returns an async generator, regardless of whether the 
    #     underlying entrypoint is sync or async.
    #     """
    #     resolved_entrypoint = self._entrypoint_resolver(
    #         entrypoint_filepath=self.agent_dir / entrypoint.file,
    #         entrypoint_module=entrypoint.module,
    #     )

    #     async def normalized_stream_runner(*input_args, **input_kwargs):
    #         console.print(f"🔍 [cyan]Entrypoint:[/cyan] {entrypoint.tag}")
    #         console.print(f"🔍 [cyan]Input data:[/cyan] *{input_args}, **{input_kwargs}")
            
    #         if inspect.isasyncgenfunction(resolved_entrypoint):
    #             # Native async generator
    #             print("resolved async generator", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
    #             async for chunk in resolved_entrypoint(*input_args, **input_kwargs):
    #                 if entrypoint.extractor:
    #                     chunk = extract_jsonpath(chunk, entrypoint.extractor)
    #                 yield chunk
    #                 await asyncio.sleep(0)
            
    #         elif inspect.iscoroutinefunction(resolved_entrypoint):
    #             # Async function that returns iterable
    #             print("resolved async function (returns iterable)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
    #             result = await resolved_entrypoint(*input_args, **input_kwargs)
    #             for chunk in result:
    #                 if entrypoint.extractor:
    #                     chunk = extract_jsonpath(chunk, entrypoint.extractor)
    #                 yield chunk
    #                 await asyncio.sleep(0)
            
    #         elif inspect.isgeneratorfunction(resolved_entrypoint):
    #             # Sync generator - consume in executor
    #             print("resolved sync generator (wrapped in async)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
    #             generator = await asyncio.get_event_loop().run_in_executor(
    #                 None, lambda: resolved_entrypoint(*input_args, **input_kwargs)
    #             )
    #             for chunk in generator:
    #                 if entrypoint.extractor:
    #                     chunk = extract_jsonpath(chunk, entrypoint.extractor)
    #                 yield chunk
    #                 await asyncio.sleep(0)
            
    #         else:
    #             # Sync function that returns iterable
    #             print("resolved sync function (returns iterable, wrapped in async)", (entrypoint.tag, entrypoint.module, resolved_entrypoint))
    #             result = await asyncio.get_event_loop().run_in_executor(
    #                 None, lambda: resolved_entrypoint(*input_args, **input_kwargs)
    #             )
    #             for chunk in result:
    #                 if entrypoint.extractor:
    #                     chunk = extract_jsonpath(chunk, entrypoint.extractor)
    #                 yield chunk
    #                 await asyncio.sleep(0)

    #     return normalized_stream_runner

    # def _entrypoint_resolver(self, entrypoint_filepath: Path, entrypoint_module: str):
    #     print(f"DEBUG: Resolving entrypoint - filepath: {entrypoint_filepath}, module: {entrypoint_module}")
    #     primary_module, secondary_attr = (
    #         entrypoint_module.split(".", 1) + [""]
    #     )[:2]
    #     print(f"DEBUG: Split module - primary: {primary_module}, secondary: {secondary_attr}")
        
    #     resolved_module = self.importer.resolve_import(
    #             entrypoint_filepath, primary_module
    #         )
    #     print(f"DEBUG: Resolved primary module: {resolved_module}")
        
    #     if secondary_attr:
    #         attrs = secondary_attr.split('.')
    #         print(f"DEBUG: Secondary attributes to resolve: {attrs}")
    #         for attr in attrs:
    #             resolved_module = getattr(resolved_module, attr)
    #             print(f"DEBUG: Resolved attribute {attr}: {resolved_module}")

    #     print(f"DEBUG: Final resolved module: {resolved_module}")
    #     print("Resolving", (entrypoint_module, resolved_module))
    #     return resolved_module

    # def _get_function_type(self, func):
    #     """
    #     Determine the type of function for debugging purposes.
    #     Returns: str describing the function type
    #     """
    #     if inspect.isasyncgenfunction(func):
    #         return "async_generator"
    #     elif inspect.iscoroutinefunction(func):
    #         return "async_function"
    #     elif inspect.isgeneratorfunction(func):
    #         return "sync_generator"
    #     else:
    #         return "sync_function"