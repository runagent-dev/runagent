from ...base_template import BaseTemplate
from typing import Dict

class LangGraphBasicTemplate(BaseTemplate):
    """Basic LangGraph framework template"""
    
    def generate_files(self) -> Dict[str, str]:
        return {
            "agent.py": self.get_runner_template(),
            "requirements.txt": self.get_requirements(),
            ".env": self.get_env_template()
        }
    
    def get_runner_template(self) -> str:
        return '''from typing import Dict, Any
from langchain.chat_models import ChatOpenAI
from langgraph.graph import Graph, END
import os
from dotenv import load_dotenv

load_dotenv()

def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basic LangGraph agent with simple workflow
    """
    try:
        # Initialize LLM
        llm = ChatOpenAI(
            temperature=input_data.get("config", {}).get("temperature", 0.7),
            model_name="gpt-4"
        )
        
        # Define a simple processing function
        def process_message(state):
            messages = state.get("messages", [])
            if messages:
                response = llm.invoke(messages[-1]["content"])
                state["response"] = response.content
            return state
        
        # Create graph
        workflow = Graph()
        workflow.add_node("process", process_message)
        workflow.add_edge("process", END)
        workflow.set_entry_point("process")
        
        # Compile and run
        app = workflow.compile()
        initial_state = {"messages": input_data.get("messages", [])}
        result = app.invoke(initial_state)
        
        return {
            "result": {
                "type": "string",
                "content": result.get("response", ""),
                "metadata": {
                    "model_used": "gpt-4",
                    "execution_time": 1.0
                }
            },
            "errors": [],
            "success": True
        }
    except Exception as e:
        return {
            "result": None,
            "errors": [str(e)],
            "success": False
        }
'''
    
    def get_requirements(self) -> str:
        return '''langchain==0.1.0
langgraph==0.0.26
openai==1.12.0
python-dotenv==1.0.0
'''
    
    def get_env_template(self) -> str:
        return '''OPENAI_API_KEY=your_openai_key_here
'''