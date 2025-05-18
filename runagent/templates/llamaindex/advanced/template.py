from ...base_template import BaseTemplate
from typing import Dict

class LlamaIndexAdvancedTemplate(BaseTemplate):
    """Advanced LlamaIndex framework template with RAG, tools, and agent"""
    
    def generate_files(self) -> Dict[str, str]:
        return {
            "agent.py": self.get_runner_template(),
            "requirements.txt": self.get_requirements(),
            ".env": self.get_env_template()
        }
    
    def get_runner_template(self) -> str:
        return '''from typing import Dict, Any, List
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    Settings,
    StorageContext,
    load_index_from_storage
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool, ToolMetadata, FunctionTool
from llama_index.core.memory import ChatMemoryBuffer
import os
from dotenv import load_dotenv

load_dotenv()

# Custom tool functions
def calculate_expression(expression: str) -> str:
    """Calculate mathematical expressions."""
    try:
        result = eval(expression)
        return f"The result is: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced LlamaIndex agent with RAG, tools, and memory
    """
    try:
        # Configure settings
        Settings.llm = OpenAI(
            model="gpt-4",
            temperature=input_data.get("config", {}).get("temperature", 0.7)
        )
        Settings.embed_model = OpenAIEmbedding()
        
        # Load or create index
        persist_dir = "./storage"
        if os.path.exists(persist_dir):
            # Load existing index
            storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            index = load_index_from_storage(storage_context)
        else:
            # Create new index (you can add documents here)
            documents = []  # Add your documents here
            index = VectorStoreIndex.from_documents(documents)
            index.storage_context.persist(persist_dir=persist_dir)
        
        # Create query engine tool
        query_engine = index.as_query_engine(similarity_top_k=3)
        query_tool = QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="knowledge_base",
                description="Search through the knowledge base for relevant information"
            )
        )
        
        # Create function tools
        calc_tool = FunctionTool.from_defaults(
            fn=calculate_expression,
            name="calculator",
            description="Calculate mathematical expressions"
        )
        
        time_tool = FunctionTool.from_defaults(
            fn=get_current_time,
            name="current_time",
            description="Get the current time"
        )
        
        # Initialize memory
        memory = ChatMemoryBuffer.from_defaults(token_limit=3000)
        
        # Load conversation history
        messages = input_data.get("messages", [])
        for msg in messages[:-1]:
            if msg["role"] == "user":
                memory.put({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                memory.put({"role": "assistant", "content": msg["content"]})
        
        # Create agent
        agent = ReActAgent.from_tools(
            tools=[query_tool, calc_tool, time_tool],
            llm=Settings.llm,
            memory=memory,
            verbose=True
        )
        
        # Get user query
        user_query = messages[-1]["content"] if messages else ""
        
        # Run agent
        response = agent.chat(user_query)
        
        return {
            "result": {
                "type": "string",
                "content": str(response),
                "metadata": {
                    "model_used": "gpt-4",
                    "tools_available": ["knowledge_base", "calculator", "current_time"],
                    "sources_used": len(response.sources) if hasattr(response, 'sources') else 0,
                    "execution_time": 2.8
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
chromadb==0.4.22
pypdf==3.17.0
'''
    
    def get_env_template(self) -> str:
        return '''OPENAI_API_KEY=your_openai_key_here
'''