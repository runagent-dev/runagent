from pathlib import Path
from runagent.sdk.server.framework.generic import GenericExecutor


class ParlantExecutor(GenericExecutor):
    """
    Executor for Parlant-based agents.
    
    Parlant is a conversational AI framework that uses guidelines, journeys, 
    and tools to create reliable, controllable AI agents.
    
    Since Parlant agents are async Python functions that return responses
    or async generators for streaming, they work perfectly with the 
    GenericExecutor's existing capabilities.
    
    Learn more: https://parlant.io
    """

    def __init__(self, agent_dir: Path):
        super().__init__(agent_dir)
        # All functionality is inherited from GenericExecutor