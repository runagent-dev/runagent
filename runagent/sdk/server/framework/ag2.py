from pathlib import Path
from runagent.sdk.server.framework.generic import GenericExecutor


class AG2Executor(GenericExecutor):
    def __init__(self, agent_dir: Path):
        super().__init__(agent_dir)
