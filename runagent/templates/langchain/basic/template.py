from ...base_template import BaseTemplate
from typing import Dict

class LangChainBasicTemplate(BaseTemplate):
    """Basic LangChain framework template"""
    
    def generate_files(self) -> Dict[str, str]:
        return {
            "agent.py": self.get_runner_template(),
            "requirements.txt": self.get_requirements(),
            ".env": self.get_env_template()
        }
    
    def get_runner_template(self) -> str:
        return '''from typing import Dict, Any
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
import os
import time
import sys
from dotenv import load_dotenv

# Initialize logging variables
logging_enabled = False
logger = None

# Import RunAgent logging
try:
    from runagent.agent_logging.log_manager import LogManager
    from runagent.constants import Framework
    
    # Get agent_id from environment or use a default
    agent_id = os.environ.get("RUNAGENT_AGENT_ID", "unknown")
    execution_id = os.environ.get("RUNAGENT_EXECUTION_ID", "unknown")
    
    # Initialize the appropriate logger
    framework_name = Framework.LANGCHAIN
    logger = LogManager.get_logger(framework_name, agent_id)
    logging_enabled = True
    
    # Log initialization
    if logging_enabled:
        logger.log_general(f"Agent initialized with ID: {agent_id}, execution ID: {execution_id}", "INFO")
except ImportError:
    logging_enabled = False
    print("RunAgent logging not available, proceeding without framework-specific logging")

# Load environment variables
load_dotenv()





def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the basic LangChain agent
    """
    start_time = time.time()
    
    try:
        if logging_enabled:
            logger.log_general(f"Starting LangChain agent execution with input: {str(input_data)[:100]}...", "INFO")
        
        llm = ChatOpenAI(
            temperature=input_data.get("config", {}).get("temperature", 0.7),
            model_name="gpt-4"
        )
        
        memory = ConversationBufferMemory()
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=True
        )
        
        messages = input_data.get("messages", [])
        last_message = messages[-1]["content"] if messages else ""
        
        if logging_enabled:
            logger.log_general(f"Processing message: {last_message[:100]}...", "INFO")
        
        result = conversation.predict(input=last_message)
        
        execution_time = time.time() - start_time
        output_data = {
            "result": {
                "type": "string",
                "content": result,
                "metadata": {
                    "model_used": "gpt-4",
                    "tokens_used": 100,
                    "execution_time": execution_time
                }
            },
            "errors": [],
            "success": True
        }
        
        if logging_enabled:
            logger.log_output(input_data, output_data)
            logger.log_general(f"LangChain agent execution completed successfully in {execution_time:.2f}s", "INFO")
        
        return output_data
    
    except Exception as e:
        execution_time = time.time() - start_time
        error_data = {
            "result": None,
            "errors": [str(e)],
            "success": False
        }
        
        if logging_enabled:
            logger.log_error(e, {"input": input_data})
            logger.log_general(f"LangChain agent execution failed: {str(e)}", "ERROR")
        
        return error_data
'''
    
    def get_requirements(self) -> str:
        return '''langchain==0.1.0
openai==1.12.0
python-dotenv==1.0.0
'''
    
    def get_env_template(self) -> str:
        return '''OPENAI_API_KEY=your_openai_key_here
'''