from ...base_template import BaseTemplate
from typing import Dict

class LlamaIndexBasicTemplate(BaseTemplate):
    """Basic LlamaIndex framework template"""
    
    def generate_files(self) -> Dict[str, str]:
        return {
            "agent.py": self.get_runner_template(),
            "requirements.txt": self.get_requirements(),
            ".env": self.get_env_template()
        }
    
    def get_runner_template(self) -> str:
        return '''from typing import Dict, Any
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basic LlamaIndex agent with simple query engine
    """
    try:
        # Configure LLM
        Settings.llm = OpenAI(
            model="gpt-4",
            temperature=input_data.get("config", {}).get("temperature", 0.7)
        )
        
        # Create a simple in-memory index (you can load documents here)
        documents = []  # Add your documents here
        index = VectorStoreIndex.from_documents(documents)
        
        # Create query engine
        query_engine = index.as_query_engine()
        
        # Get user query
        messages = input_data.get("messages", [])
        user_query = messages[-1]["content"] if messages else ""
        
        # Query the index
        response = query_engine.query(user_query)
        
        return {
            "result": {
                "type": "string",
                "content": str(response),
                "metadata": {
                    "model_used": "gpt-4",
                    "source_nodes": len(response.source_nodes) if hasattr(response, 'source_nodes') else 0,
                    "execution_time": 1.2
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
        return '''llama-index==0.10.0
openai==1.12.0
python-dotenv==1.0.0
'''
    
    def get_env_template(self) -> str:
        return '''OPENAI_API_KEY=your_openai_key_here
'''
