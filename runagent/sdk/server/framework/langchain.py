from pathlib import Path
from typing import Dict, Any

from runagent.sdk.server.framework.generic import GenericExecutor
from runagent.utils.schema import EntryPoint


class LangChainExecutor(GenericExecutor):
    """Executor for LangChain agents with framework-specific input handling"""
    
    def __init__(self, agent_dir: Path, agent_entrypoints: Dict[str, EntryPoint]):
        super().__init__(agent_dir, agent_entrypoints)

    def generic(self, *input_args, **input_kwargs):
        """
        LangChain-specific generic execution that formats inputs correctly
        """
        if self._generic_entrypoint is None:
            raise ValueError("No `generic` entrypoint found in agent config")
        
        print(f"DEBUG: LangChain generic execution with args: {input_args}, kwargs: {input_kwargs}")
        
        # Convert inputs to LangChain's expected format
        input_data = self._format_langchain_input(*input_args, **input_kwargs)
        
        print(f"DEBUG: LangChain formatted input: {input_data}")
        
        try:
            # Call the LangChain run function with properly formatted input_data
            result_obj = self._generic_entrypoint(input_data)
            result_json = self.serializer.serialize_object(result_obj)
            return result_json
            
        except Exception as e:
            print(f"ERROR: LangChain execution failed: {e}")
            print(f"ERROR: Entrypoint type: {type(self._generic_entrypoint)}")
            raise

    def _format_langchain_input(self, *input_args, **input_kwargs) -> Dict[str, Any]:
        """
        Convert generic inputs to LangChain's expected input_data format
        
        LangChain expects: {"messages": [...], "config": {...}}
        """
        input_data = {"config": {}}
        
        # Handle different input patterns
        if len(input_args) == 1 and isinstance(input_args[0], dict):
            # Single dict argument - use as base
            base_data = input_args[0]
            if "messages" in base_data:
                input_data.update(base_data)
            else:
                # Convert dict to messages format
                input_data["messages"] = [{"role": "user", "content": str(base_data)}]
        
        elif len(input_args) == 1 and isinstance(input_args[0], str):
            # Single string argument - convert to message
            input_data["messages"] = [{"role": "user", "content": input_args[0]}]
        
        elif input_args:
            # Multiple args - convert to messages
            content = " ".join(str(arg) for arg in input_args)
            input_data["messages"] = [{"role": "user", "content": content}]
        
        # Handle keyword arguments
        if "messages" in input_kwargs:
            # Direct messages provided
            input_data["messages"] = input_kwargs["messages"]
        
        elif "query" in input_kwargs or "message" in input_kwargs:
            # Query/message format - convert to messages
            content = input_kwargs.get("query") or input_kwargs.get("message")
            input_data["messages"] = [{"role": "user", "content": str(content)}]
        
        elif input_kwargs and "messages" not in input_data:
            # Other kwargs - convert to message content
            content = str(input_kwargs)
            input_data["messages"] = [{"role": "user", "content": content}]
        
        # Add config from kwargs
        if "config" in input_kwargs:
            input_data["config"].update(input_kwargs["config"])
        
        # Add other relevant kwargs to config
        config_keys = ["temperature", "model", "verbose", "max_iterations"]
        for key in config_keys:
            if key in input_kwargs:
                input_data["config"][key] = input_kwargs[key]
        
        # Ensure we have messages
        if "messages" not in input_data or not input_data["messages"]:
            input_data["messages"] = [{"role": "user", "content": "Hello"}]
        
        return input_data

    async def generic_stream(self, *input_args, **input_kwargs):
        """
        LangChain-specific streaming execution
        """
        if self._generic_stream_entrypoint is None:
            raise ValueError("No `generic_stream` entrypoint found in agent config")

        # Format input the same way
        input_data = self._format_langchain_input(*input_args, **input_kwargs)
        
        try:
            # For LangChain streaming (if implemented)
            for chunk in self._generic_stream_entrypoint(input_data):
                yield chunk
        except Exception as e:
            print(f"ERROR: LangChain stream execution failed: {e}")
            raise