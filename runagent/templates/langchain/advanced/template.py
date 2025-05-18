from ...base_template import BaseTemplate
from typing import Dict

class LangChainAdvancedTemplate(BaseTemplate):
    """Advanced LangChain framework template with tools, agent, and memory"""
    
    def generate_files(self) -> Dict[str, str]:
        return {
            "agent.py": self.get_runner_template(),
            "requirements.txt": self.get_requirements(),
            ".env": self.get_env_template()
        }
    
    def get_runner_template(self) -> str:
        return '''from typing import Dict, Any, List
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool, tool
from langchain.schema import HumanMessage, AIMessage, SystemMessage
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

# Define custom tools
@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        if logging_enabled:
            logger.log_general(f"Using calculate tool with expression: {expression}", "INFO")
        result = eval(expression)
        return f"The result is: {result}"
    except Exception as e:
        if logging_enabled:
            logger.log_error(e, {"expression": expression})
        return f"Error in calculation: {str(e)}"

@tool
def search_knowledge(query: str) -> str:
    """Search for information in the knowledge base."""
    if logging_enabled:
        logger.log_general(f"Using search_knowledge tool with query: {query}", "INFO")
    # Implement your custom search logic here
    return f"Search results for '{query}': [Placeholder for actual search results]"

def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced LangChain agent with tools, memory, and custom prompt
    """
    start_time = time.time()
    
    try:
        if logging_enabled:
            logger.log_general(f"Starting advanced LangChain agent with tools", "INFO")
        
        # Initialize tools
        tools = [calculate, search_knowledge]
        
        # Initialize LLM
        llm = ChatOpenAI(
            temperature=input_data.get("config", {}).get("temperature", 0.7),
            model_name="gpt-4",
            streaming=True
        )
        
        # Create custom prompt
        system_prompt = input_data.get("config", {}).get(
            "system_prompt", 
            "You are a helpful AI assistant with access to tools for calculation and knowledge search."
        )
        
        if logging_enabled:
            logger.log_general(f"Using system prompt: {system_prompt[:100]}...", "INFO")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Initialize memory
        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=5  # Keep last 5 messages
        )
        
        # Load conversation history if provided
        messages = input_data.get("messages", [])
        for msg in messages[:-1]:  # All except the last message
            if msg["role"] == "user":
                memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                memory.chat_memory.add_ai_message(msg["content"])
        
        # Get the last user message
        last_message = messages[-1]["content"] if messages else ""
        
        if logging_enabled:
            logger.log_general(f"Processing message: {last_message[:100]}...", "INFO")
        
        # Create agent
        agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True
        )
        
        # Run agent
        result = agent_executor.invoke({"input": last_message})
        
        execution_time = time.time() - start_time
        output_data = {
            "result": {
                "type": "string",
                "content": result["output"],
                "metadata": {
                    "model_used": "gpt-4",
                    "tools_used": [t.name for t in tools],
                    "conversation_history": len(messages),
                    "execution_time": execution_time
                }
            },
            "errors": [],
            "success": True
        }
        
        if logging_enabled:
            logger.log_output(input_data, output_data)
            logger.log_general(f"Advanced LangChain agent execution completed in {execution_time:.2f}s", "INFO")
            # Log tools used if any
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    if logging_enabled:
                        tool_name = step[0].tool
                        tool_input = step[0].tool_input
                        tool_output = step[1]
                        logger.log_general(f"Tool used: {tool_name} with input: {tool_input}", "INFO")
        
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
            logger.log_general(f"Advanced LangChain agent execution failed: {str(e)}", "ERROR")
        
        return error_data
'''
    
    def get_requirements(self) -> str:
        return '''langchain==0.1.0
openai==1.12.0
python-dotenv==1.0.0
chromadb==0.4.22
tiktoken==0.5.2
'''
    
    def get_env_template(self) -> str:
        return '''OPENAI_API_KEY=your_openai_key_here
SERPAPI_API_KEY=your_serpapi_key_here
'''