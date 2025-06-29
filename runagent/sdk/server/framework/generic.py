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
        """
        Enhanced entrypoint resolver that handles:
        - Functions: "solve_problem"
        - Object methods: "app.invoke" 
        - Class methods: "MyClass.method"
        - Nested attributes: "obj.attr.method"
        """
        print(f"DEBUG: Resolving entrypoint - filepath: {entrypoint_filepath}, module: {entrypoint_module}")
        
        # Split the module path
        module_parts = entrypoint_module.split(".")
        primary_module = module_parts[0]
        attribute_chain = module_parts[1:] if len(module_parts) > 1 else []
        
        print(f"DEBUG: Primary module: {primary_module}, Attribute chain: {attribute_chain}")
        
        # Import the primary module/object
        try:
            resolved_module = self.importer.resolve_import(
                entrypoint_filepath, primary_module
            )
            print(f"DEBUG: Resolved primary module: {resolved_module}")
        except Exception as e:
            print(f"ERROR: Failed to resolve primary module '{primary_module}': {e}")
            raise
        
        # Navigate through the attribute chain
        current_object = resolved_module
        for i, attr in enumerate(attribute_chain):
            print(f"DEBUG: Resolving attribute '{attr}' on {type(current_object)}")
            try:
                if hasattr(current_object, attr):
                    current_object = getattr(current_object, attr)
                    print(f"DEBUG: Successfully resolved '{attr}' -> {type(current_object)}")
                else:
                    # Try to handle special cases
                    available_attrs = [a for a in dir(current_object) if not a.startswith('_')]
                    print(f"ERROR: Attribute '{attr}' not found. Available attributes: {available_attrs}")
                    raise AttributeError(f"'{type(current_object).__name__}' object has no attribute '{attr}'")
            except Exception as e:
                print(f"ERROR: Failed to resolve attribute '{attr}': {e}")
                raise
        
        print(f"DEBUG: Final resolved entrypoint: {current_object}")
        
        # Validate that the final object is callable
        if not callable(current_object):
            raise ValueError(f"Entrypoint '{entrypoint_module}' resolved to non-callable object: {type(current_object)}")
        
        return current_object

    def generic(self, *input_args, **input_kwargs):
        if self._generic_entrypoint is None:
            raise ValueError("No `generic` entrypoint found in agent config")
        
        print(f"DEBUG: Calling entrypoint with args: {input_args}, kwargs: {input_kwargs}")
        
        # Smart argument handling based on the type of entrypoint
        try:
            # Check if this looks like a LangGraph app.invoke method
            if hasattr(self._generic_entrypoint, '__self__') and hasattr(self._generic_entrypoint.__self__, 'invoke'):
                # This is likely a method on a LangGraph app
                print("DEBUG: Detected LangGraph-style app.invoke method")
                
                # Convert arguments to LangGraph state format
                if input_kwargs:
                    # Use kwargs as the state
                    langgraph_input = input_kwargs
                elif input_args and len(input_args) == 1 and isinstance(input_args[0], dict):
                    # Single dict argument
                    langgraph_input = input_args[0]
                elif input_args:
                    # Convert positional args to state
                    langgraph_input = {"input": input_args[0] if len(input_args) == 1 else input_args}
                else:
                    langgraph_input = {}
                
                print(f"DEBUG: LangGraph input: {langgraph_input}")
                result_obj = self._generic_entrypoint(langgraph_input)
            else:
                # Regular function call
                print("DEBUG: Regular function call")
                result_obj = self._generic_entrypoint(*input_args, **input_kwargs)
            
            result_json = self.serializer.serialize_object(result_obj)
            return result_json
            
        except Exception as e:
            print(f"ERROR: Entrypoint execution failed: {e}")
            print(f"ERROR: Entrypoint type: {type(self._generic_entrypoint)}")
            if hasattr(self._generic_entrypoint, '__self__'):
                print(f"ERROR: Entrypoint self: {type(self._generic_entrypoint.__self__)}")
            raise

    async def generic_stream(self, *input_args, **input_kwargs):
        if self._generic_stream_entrypoint is None:
            raise ValueError("No `generic_stream` entrypoint found in agent config")

        # Similar logic for streaming
        try:
            if hasattr(self._generic_stream_entrypoint, '__self__') and hasattr(self._generic_stream_entrypoint.__self__, 'stream'):
                # LangGraph app.stream method
                if input_kwargs:
                    langgraph_input = input_kwargs
                elif input_args and len(input_args) == 1 and isinstance(input_args[0], dict):
                    langgraph_input = input_args[0]
                else:
                    langgraph_input = {"input": input_args[0] if len(input_args) == 1 else input_args}
                
                for chunk in self._generic_stream_entrypoint(langgraph_input):
                    yield chunk
                    await asyncio.sleep(0)
            else:
                # Regular generator function
                for chunk in self._generic_stream_entrypoint(*input_args, **input_kwargs):
                    yield chunk
                    await asyncio.sleep(0)
        except Exception as e:
            print(f"ERROR: Stream entrypoint execution failed: {e}")
            raise

    