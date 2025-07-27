import asyncio
import httpx
import inspect
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from runagent.utils.imports import PackageImporter
from runagent.utils.schema import WebHookEntryPoint, RunAgentConfig
from runagent.utils.serializer import CoreSerializer
from runagent.utils.response import extract_jsonpath, to_dict

console = Console()


class N8NExecutor:

    rerserved_tags = list()

    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir

    def get_runner(self, entrypoint: WebHookEntryPoint):
        """
        Always returns an async function, regardless of whether the 
        underlying entrypoint is sync or async.
        """
        # resolved_entrypoint = self._entrypoint_resolver(
        #     entrypoint_filepath=self.agent_dir / entrypoint.file,
        #     entrypoint_module=entrypoint.module,
        # )

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

            timeout = httpx.Timeout(
                timeout=entrypoint.timeout,  # 60 seconds total timeout
                connect=10.0,  # 10 seconds to connect
                read=50.0,     # 50 seconds to read response
                write=10.0     # 10 seconds to write request
            )
            async with httpx.AsyncClient(timeout=timeout) as client:
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

        return normalized_runner
