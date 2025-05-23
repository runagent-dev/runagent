import functools
from typing import Dict, Any
from runagent.logging.log_manager import LogManager
from runagent.monitoring.status_manager import StatusManager
from runagent.monitoring.agent_status import AgentState

def with_logging(framework: str, agent_id: str):
    """Decorator to add logging to the run function"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(input_data: Dict[str, Any]) -> Dict[str, Any]:
            logger = LogManager.get_logger(framework, agent_id)
            status_manager = StatusManager()
            
            try:
                # Update status to running
                status_manager.update_status(agent_id, AgentState.RUNNING)
                logger.log_general(f"Starting agent execution for {agent_id}")
                
                # Execute the function
                result = func(input_data)
                
                # Log input/output
                logger.log_output(input_data, result)
                
                # Update status based on result
                if result.get("success", False):
                    status_manager.update_status(agent_id, AgentState.COMPLETED)
                    logger.log_general(f"Agent {agent_id} completed successfully")
                else:
                    status_manager.update_status(agent_id, AgentState.FAILED)
                    logger.log_general(f"Agent {agent_id} failed", "ERROR")
                
                return result
                
            except Exception as e:
                # Log error
                logger.log_error(e, {"input": input_data})
                
                # Parse framework-specific error
                error_details = logger.parse_framework_specific_error(e)
                logger.log_general(f"Framework error: {error_details}", "ERROR")
                
                # Update status
                status_manager.update_status(
                    agent_id, 
                    AgentState.FAILED,
                    metadata={"error": str(e)}
                )
                
                return {
                    "result": None,
                    "errors": [str(e)],
                    "success": False
                }
        
        return wrapper
    return decorator
