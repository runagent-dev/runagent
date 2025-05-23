from typing import Type, Dict
from runagent.templates.base_template import BaseTemplate
from runagent.templates.langgraph import LangGraphBasicTemplate, LangGraphAdvancedTemplate
from runagent.templates.langchain import LangChainBasicTemplate, LangChainAdvancedTemplate
from runagent.templates.llamaindex import LlamaIndexBasicTemplate, LlamaIndexAdvancedTemplate

from runagent.constants import Framework


def get_standalone_logging_module() -> str:
    return '''
# standalone_logging.py - Bundled with the agent
import os
import json
import time
from datetime import datetime
import traceback
import sys

class AgentLogger:
    """Standalone logger that works without RunAgent dependencies"""
    
    def __init__(self, agent_id=None, framework=None):
        self.agent_id = agent_id or os.environ.get("RUNAGENT_AGENT_ID", "unknown")
        self.framework = framework or os.environ.get("RUNAGENT_FRAMEWORK", "unknown")
        self.execution_id = os.environ.get("RUNAGENT_EXECUTION_ID", "unknown")
        
        # Create logs directory at the root of the execution directory
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize log files
        self.general_log = os.path.join(self.log_dir, "general.log")
        self.output_log = os.path.join(self.log_dir, "output.log")
        self.error_log = os.path.join(self.log_dir, "error.log")
        
    def log_general(self, message, level="INFO"):
        """Log general information"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "framework": self.framework
        }
        
        try:
            with open(self.general_log, "a") as f:
                f.write(json.dumps(log_entry) + "\\n")
            
            # Also print to console for visibility
            print(f"[{timestamp}] {level}: {message}")
        except Exception as e:
            print(f"Error writing to general log: {str(e)}")
    
    def log_output(self, input_data, output_data):
        """Log input and output data"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "output": output_data,
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "framework": self.framework
        }
        
        try:
            with open(self.output_log, "a") as f:
                f.write(json.dumps(log_entry) + "\\n")
        except Exception as e:
            print(f"Error writing to output log: {str(e)}")
    
    def log_error(self, error, context=None):
        """Log error information"""
        context = context or {}
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context,
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "framework": self.framework
        }
        
        try:
            with open(self.error_log, "a") as f:
                f.write(json.dumps(error_data) + "\\n")
            
            # Also print to console for visibility
            print(f"ERROR: {str(error)}")
        except Exception as e:
            print(f"Error writing to error log: {str(e)}")

def get_logger(framework=None, agent_id=None):
    """Create a logger instance"""
    return AgentLogger(agent_id=agent_id, framework=framework)
'''

class TemplateFactory:
    """Factory for creating framework templates"""
    
    # Template registry
    _templates: Dict[str, Dict[str, Type[BaseTemplate]]] = {
        Framework.LANGGRAPH: {
            "basic": LangGraphBasicTemplate,
            "advanced": LangGraphAdvancedTemplate
        },
        Framework.LANGCHAIN: {
            "basic": LangChainBasicTemplate,
            "advanced": LangChainAdvancedTemplate
        },
        Framework.LLAMAINDEX: {
            "basic": LlamaIndexBasicTemplate,
            "advanced": LlamaIndexAdvancedTemplate
        }
    }
    
    @classmethod
    def get_template(cls, framework: str, level: str = "basic") -> BaseTemplate:
        """
        Get template instance for framework and complexity level
        
        Args:
            framework: Framework name (langgraph, langchain, llamaindex)
            level: Complexity level (basic, advanced)
            
        Returns:
            Template instance
        """
        if framework not in cls._templates:
            raise ValueError(f"Unsupported framework: {framework}")
        
        if level not in cls._templates[framework]:
            raise ValueError(f"Unsupported level '{level}' for framework '{framework}'")
        
        template_class = cls._templates[framework][level]
        
        # Create enhanced template with logging support
        template_instance = template_class()
        template_instance = cls._enhance_template_with_logging(template_instance, framework)
        
        return template_instance
    
    @classmethod
    def _enhance_template_with_logging(cls, template: BaseTemplate, framework: str) -> BaseTemplate:
        """
        Enhance template with framework-specific logging
        
        Args:
            template: Original template instance
            framework: Framework name
            
        Returns:
            Enhanced template instance with logging
        """
        # Store original methods
        original_get_runner = template.get_runner_template
        original_generate_files = template.generate_files
        
        # Add standalone logging module
        def enhanced_generate_files() -> Dict[str, str]:
            files = original_generate_files()
            # Add standalone logging module
            files["standalone_logging.py"] = get_standalone_logging_module()
            return files
        
        # Define enhanced method with logging
        def enhanced_get_runner_template() -> str:
            runner_code = original_get_runner()
            
            # Add logging imports and initialization
            logging_init = f'''
# Initialize logging
import os
import time
from datetime import datetime

# Try to import standalone logging module
try:
    from standalone_logging import get_logger
    
    # Get agent_id and framework from environment or use defaults
    agent_id = os.environ.get("RUNAGENT_AGENT_ID", "unknown")
    framework = os.environ.get("RUNAGENT_FRAMEWORK", "{framework}")
    
    # Initialize logger
    logger = get_logger(framework=framework, agent_id=agent_id)
    logging_enabled = True
    
    # Log initialization
    logger.log_general(f"Agent initialized with framework: {{framework}}, agent ID: {{agent_id}}")
except ImportError as e:
    logging_enabled = False
    print(f"Warning: Standalone logging not available: {{str(e)}}")
'''
            
            # Add time import for execution time tracking
            time_import = 'import time\n'
            
            # Add logging to the run function
            if 'def run(' in runner_code:
                start_time_code = '''
    # Execution time tracking
    start_time = time.time()
    
    # Log execution start
    if logging_enabled:
        logger.log_general(f"Starting agent execution with input: {str(input_data)[:100]}...", "INFO")
'''
                
                end_time_success_code = '''
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Add execution time to metadata
        if isinstance(output_data, dict) and "result" in output_data and isinstance(output_data["result"], dict):
            if "metadata" not in output_data["result"]:
                output_data["result"]["metadata"] = {}
            output_data["result"]["metadata"]["execution_time"] = execution_time
        
        # Log successful execution
        if logging_enabled:
            logger.log_output(input_data, output_data)
            logger.log_general(f"Agent execution completed successfully in {execution_time:.2f}s", "INFO")
'''
                
                end_time_error_code = '''
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Create error response
        error_data = {
            "result": None,
            "errors": [str(e)],
            "success": False
        }
        
        # Log error
        if logging_enabled:
            logger.log_error(e, {"input": input_data})
            logger.log_general(f"Agent execution failed: {str(e)}", "ERROR")
        
        return error_data
'''
                
                # Replace the run function with logging
                # Find where the run function starts
                run_start_idx = runner_code.find('def run(')
                if run_start_idx >= 0:
                    # Insert imports at the beginning
                    enhanced_code = runner_code[:run_start_idx]
                    if 'import time' not in enhanced_code:
                        enhanced_code = enhanced_code.rstrip() + '\n' + time_import
                    
                    # Add logging initialization
                    enhanced_code += logging_init + '\n' + runner_code[run_start_idx:]
                    
                    # Add start time tracking after the function definition starts
                    run_body_start = enhanced_code.find(':', run_start_idx)
                    if run_body_start >= 0:
                        enhanced_code = enhanced_code[:run_body_start+1] + start_time_code + enhanced_code[run_body_start+1:]
                    
                    # Find try-except block if it exists
                    try_start_idx = enhanced_code.find('    try:', run_body_start)
                    if try_start_idx >= 0:
                        # Find the return statement in the try block
                        return_idx = enhanced_code.find('        return ', try_start_idx)
                        if return_idx >= 0:
                            # Get the return variable name
                            return_line = enhanced_code[return_idx:enhanced_code.find('\n', return_idx)]
                            if 'return {' in return_line:
                                # Inline return, add logging before
                                enhanced_code = enhanced_code[:return_idx] + end_time_success_code + \
                                              enhanced_code[return_idx:]
                            else:
                                # Variable return
                                result_var = return_line.strip().replace('return ', '')
                                # Add output_data = result_var before logging
                                enhanced_code = enhanced_code[:return_idx] + \
                                              f'        output_data = {result_var}\n' + \
                                              end_time_success_code + \
                                              enhanced_code[return_idx:]
                        
                        # Find the except block
                        except_start_idx = enhanced_code.find('    except', try_start_idx)
                        if except_start_idx >= 0:
                            # Find the return in the except block
                            except_return_idx = enhanced_code.find('        return', except_start_idx)
                            if except_return_idx >= 0:
                                # Replace with error logging
                                except_end_idx = enhanced_code.find('\n', except_return_idx)
                                enhanced_code = enhanced_code[:except_return_idx] + end_time_error_code + \
                                              enhanced_code[except_end_idx+1:]
                            else:
                                # Add error logging at the end of except block
                                except_block_end = enhanced_code.find('    ', except_start_idx + 10)
                                if except_block_end == -1:
                                    except_block_end = len(enhanced_code)
                                enhanced_code = enhanced_code[:except_block_end] + end_time_error_code + \
                                              enhanced_code[except_block_end:]
                    else:
                        # No try-except, add basic logging before return
                        return_idx = enhanced_code.find('    return', run_body_start)
                        if return_idx >= 0:
                            enhanced_code = enhanced_code[:return_idx] + \
                                          '    # Add execution time tracking\n' + \
                                          '    execution_time = time.time() - start_time\n' + \
                                          '    if logging_enabled:\n' + \
                                          '        logger.log_general(f"Agent execution completed in {execution_time:.2f}s", "INFO")\n\n' + \
                                          enhanced_code[return_idx:]
                    
                    runner_code = enhanced_code
            
            return runner_code
        
        # Replace the methods with enhanced versions
        template.get_runner_template = enhanced_get_runner_template
        template.generate_files = enhanced_generate_files
        
        return template
    
    @classmethod
    def list_available_templates(cls) -> Dict[str, list]:
        """List all available templates"""
        return {
            framework: list(levels.keys())
            for framework, levels in cls._templates.items()
        }
    
    @classmethod
    def register_template(cls, framework: str, level: str, template_class: Type[BaseTemplate]):
        """Register a new template"""
        if framework not in cls._templates:
            cls._templates[framework] = {}
        cls._templates[framework][level] = template_class

