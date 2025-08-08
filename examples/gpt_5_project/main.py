from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import json
import uuid
import subprocess
import threading
import time
from typing import Dict, List, Optional
from openai import OpenAI
import shutil
from pathlib import Path

app = FastAPI(title="RunAgent Generator API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize OpenAI client
openai_client = OpenAI()

# In-memory storage for sessions and running agents
sessions: Dict[str, dict] = {}
running_agents: Dict[str, dict] = {}

# Load templates from documents for RAG
TEMPLATES = {
    "langgraph": {
        "basic": {
            "files": [
                "agents.py",
                "requirements.txt", 
                "runagent.config.json"
            ],
            "description": "Simple LangGraph Problem Solver with two-agent workflow"
        },
        "advanced": {
            "files": [
                "agent.py",
                "main.py", 
                "requirements.txt"
            ],
            "description": "Advanced LangGraph agent with conditional routing and tools"
        }
    },
    "letta": {
        "basic": {
            "files": [
                "agent.py",
                "run.py",
                "runagent.config.json"
            ],
            "description": "Simple Letta agent for conversational AI"
        },
        "advanced": {
            "files": [
                "agent.py",
                "keyword_tool.py",
                "run.py",
                "runagent.config.json"
            ],
            "description": "Advanced Letta agent with custom tools"
        }
    },
    "agno": {
        "basic": {
            "files": [
                "simple_assistant.py",
                "requirements.txt",
                "runagent.config.json"
            ],
            "description": "Simple Agno assistant agent"
        }
    },
    "llamaindex": {
        "basic": {
            "files": [
                "math_genius.py",
                "requirements.txt", 
                "runagent.config.json"
            ],
            "description": "LlamaIndex math agent with function tools"
        }
    }
}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    stage: str  # "understanding", "planning", "generating", "complete"
    description: Optional[str] = None
    mermaid_diagram: Optional[str] = None
    agent_id: Optional[str] = None
    agent_url: Optional[str] = None

def analyze_user_request(message: str) -> dict:
    """Use GPT-5 to analyze user request and extract agent requirements."""
    
    prompt = f"""
    Analyze this user request for creating an AI agent: "{message}"
    
    Extract and return a JSON with:
    1. agent_name: A concise name for the agent
    2. framework: One of [langgraph, letta, agno, llamaindex] 
    3. template_type: "basic" or "advanced"
    4. description: What the agent does (2-3 sentences)
    5. main_functionality: Primary purpose
    6. input_fields: List of input field names the agent needs
    7. backend_language: "python" or "typescript" (default python unless specified)
    
    Choose framework based on:
    - langgraph: Complex workflows, multi-agent systems, decision trees
    - letta: Conversational AI, memory-based agents, chat interfaces  
    - agno: Simple assistants, analysis tasks, reporting
    - llamaindex: RAG, document processing, knowledge retrieval
    
    Return only valid JSON.
    """
    
    try:
        # Using GPT-5 Responses API
        response = openai_client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            reasoning={"effort": "minimal"}
        )
        
        # Extract content from GPT-5 response
        content = response.output[1].content[0].text  # Get the text from output message
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Error analyzing request: {e}")
        return {
            "agent_name": "custom_agent",
            "framework": "agno",
            "template_type": "basic", 
            "description": "A custom AI agent",
            "main_functionality": "General assistance",
            "input_fields": ["message"],
            "backend_language": "python"
        }

def generate_mermaid_diagram(agent_info: dict) -> str:
    """Generate dynamic Mermaid diagram using GPT-5 with improved validation."""
    
    prompt = f"""
    Create a valid Mermaid flowchart diagram for an AI agent with these specifications:
    
    Agent Name: {agent_info['agent_name']}
    Framework: {agent_info['framework']}
    Description: {agent_info['description']}
    Main Functionality: {agent_info['main_functionality']}
    Input Fields: {agent_info['input_fields']}
    
    IMPORTANT REQUIREMENTS:
    1. Start with "graph TD" (Top Down layout)
    2. Use simple node IDs (A, B, C, etc.)
    3. Use only basic shapes: rectangles [text], diamonds {{text}}, and circles ((text))
    4. Use only --> arrows
    5. Keep node text short (under 20 characters)
    6. Maximum 8-10 nodes total
    7. No special characters in node text except spaces and basic punctuation
    
    Create a workflow showing:
    - Input processing (start with user input)
    - Framework-specific processing steps for {agent_info['framework']}
    - Main functionality: {agent_info['main_functionality']}
    - Output generation
    
    EXAMPLE FORMAT:
    graph TD
        A[User Input] --> B[Parse Query]
        B --> C[{agent_info['framework']} Processing]
        C --> D[Generate Response]
        D --> E[Return Result]
    
    Return ONLY the Mermaid code. No explanations, no markdown blocks, no extra text.
    """
    
    try:
        print("🎨 Generating Mermaid diagram with GPT-5...")
        
        # Use GPT-5 for dynamic diagram generation
        response = openai_client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            reasoning={"effort": "minimal"}  # Keep it simple
        )
        
        # Extract the Mermaid code from GPT-5 response
        mermaid_code = response.output[1].content[0].text.strip()
        
        print(f"🔍 Raw GPT-5 output: {mermaid_code}")
        
        # Clean up the response more thoroughly
        mermaid_code = mermaid_code.replace('```mermaid', '').replace('```', '').strip()
        
        # Remove any leading/trailing whitespace from each line
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        mermaid_code = '\n    '.join(lines)
        
        # Ensure it starts with a valid Mermaid declaration
        if not mermaid_code.startswith(('graph TD', 'graph LR', 'flowchart TD', 'flowchart LR')):
            mermaid_code = f"graph TD\n    {mermaid_code}"
        
        # Basic validation - check for required elements
        if '-->' not in mermaid_code:
            raise Exception("Generated diagram missing arrows (-->)")
        
        # Validate node format - should have at least some nodes
        import re
        nodes = re.findall(r'[A-Z]\d*\[.*?\]', mermaid_code)
        if len(nodes) < 2:
            raise Exception(f"Generated diagram has too few nodes: {len(nodes)}")
        
        print(f"✅ Generated valid Mermaid diagram with {len(nodes)} nodes")
        print(f"📋 Final Mermaid code:\n{mermaid_code}")
        
        return mermaid_code
        
    except Exception as e:
        print(f"❌ Error generating Mermaid diagram: {e}")

def validate_mermaid_syntax(mermaid_code: str) -> tuple[bool, str]:
    """Validate Mermaid syntax before sending to frontend."""
    
    try:
        # Basic syntax checks
        if not mermaid_code.strip():
            return False, "Empty diagram code"
        
        if not any(mermaid_code.startswith(prefix) for prefix in ['graph TD', 'graph LR', 'flowchart TD', 'flowchart LR']):
            return False, "Missing graph declaration"
        
        if '-->' not in mermaid_code:
            return False, "No arrows found in diagram"
        
        # Check for balanced brackets
        open_brackets = mermaid_code.count('[') + mermaid_code.count('{') + mermaid_code.count('(')
        close_brackets = mermaid_code.count(']') + mermaid_code.count('}') + mermaid_code.count(')')
        
        if open_brackets != close_brackets:
            return False, f"Unbalanced brackets: {open_brackets} open, {close_brackets} close"
        
        # Check for valid node IDs
        import re
        node_pattern = r'[A-Z]\d*(?:\[.*?\]|\{.*?\}|\(.*?\))?'
        nodes = re.findall(node_pattern, mermaid_code)
        
        if len(nodes) < 2:
            return False, f"Too few nodes found: {len(nodes)}"
        
        return True, "Valid Mermaid syntax"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def generate_custom_framework_files(agent_info: dict, session_dir: Path):
    """Generate custom framework files with proper required fields."""
    
    agent_code = f'''"""
{agent_info['agent_name']} - {agent_info['description']}
Generated by RunAgent Generator - Custom Framework
"""

def main(*input_args, **input_kwargs):
    """Main entry point for custom agent"""
    
    # Extract input from various sources
    user_input = ""
    for field in {agent_info['input_fields']}:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    if not user_input:
        user_input = "Hello, how can I help you?"
    
    # Simple response for custom framework
    response = f"""
    Hello! I'm {agent_info['agent_name']}.
    
    {agent_info['description']}
    
    You asked: {{user_input}}
    
    My main functionality is: {agent_info['main_functionality']}
    
    This is a custom framework implementation. You can modify this code to add your specific logic.
    """
    
    return response

def main_stream(*input_args, **input_kwargs):
    """Streaming entry point for custom agent"""
    
    # Get the main response
    response = main(*input_args, **input_kwargs)
    
    # Simulate streaming by yielding words
    words = response.split()
    for i, word in enumerate(words):
        if i == 0:
            yield word
        else:
            yield f" {{word}}"
        
        # Add small delay for demonstration
        import time
        time.sleep(0.01)
'''
    
    with open(session_dir / "agent.py", "w") as f:
        f.write(agent_code)
    
    # Generate minimal requirements
    with open(session_dir / "requirements.txt", "w") as f:
        f.write("# No additional requirements for custom framework\n")
    
    # Generate config with ALL required fields
    config = {
        "agent_name": agent_info['agent_name'],
        "description": agent_info['description'],
        "framework": "custom",
        "template": "custom",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "template_source": {
            "repo_url": "https://github.com/runagent-dev/runagent.git",
            "path": "templates/custom/basic",
            "author": "runagent-generator",
            "version": "1.0.0"
        },
        "agent_architecture": {
            "entrypoints": [
                {
                    "file": "agent.py",
                    "module": "main",
                    "tag": "main"
                },
                {
                    "file": "agent.py",
                    "module": "main_stream",
                    "tag": "main_stream"
                }
            ]
        },
        "input_fields": agent_info['input_fields'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Generated custom framework config with required fields")
        
def generate_agent_files(agent_info: dict, session_id: str) -> bool:
    """Generate agent files based on template and user requirements."""
    
    framework = agent_info['framework']
    template_type = agent_info.get('template_type', 'basic')
    
    # Create session directory
    session_dir = Path(f"generated_agents/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Create .env file with OpenAI API key
    env_content = f"""# OpenAI API Key
OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')}

# Letta Configuration (if using Letta)
LETTA_SERVER_URL=http://localhost:8283

# RunAgent Configuration
RUNAGENT_DISABLE_DB=true
RUNAGENT_NO_DATABASE=true
RUNAGENT_LOG_LEVEL=INFO
"""
    
    with open(session_dir / ".env", "w") as f:
        f.write(env_content)
    
    try:
        print(f"🔧 Generating {framework} agent files...")
        
        if framework == "langgraph":
            generate_langgraph_files(agent_info, session_dir)
        elif framework == "letta":
            generate_letta_files(agent_info, session_dir)
        elif framework == "agno":
            generate_agno_files(agent_info, session_dir)
        elif framework == "llamaindex":
            generate_llamaindex_files(agent_info, session_dir)
        else:
            # Default/custom framework
            generate_custom_framework_files(agent_info, session_dir)
        
        # Verify the config file was created and is valid
        config_file = session_dir / "runagent.config.json"
        if not config_file.exists():
            raise Exception("Config file was not created")
        
        # Validate the config file
        with open(config_file, "r") as f:
            config = json.load(f)
        
        # Check for required fields
        required_fields = ["agent_name", "description", "framework", "template_source", "agent_architecture"]
        missing_fields = []
        
        for field in required_fields:
            if field not in config:
                missing_fields.append(field)
        
        if missing_fields:
            raise Exception(f"Config missing required fields: {missing_fields}")
        
        # Validate template_source structure
        if not isinstance(config.get("template_source"), dict):
            raise Exception("template_source must be a dictionary")
        
        template_source = config["template_source"]
        required_template_fields = ["repo_url", "path", "author", "version"]
        missing_template_fields = []
        
        for field in required_template_fields:
            if field not in template_source:
                missing_template_fields.append(field)
        
        if missing_template_fields:
            raise Exception(f"template_source missing required fields: {missing_template_fields}")
        
        print(f"✅ Successfully generated and validated {framework} agent")
        return True
        
    except Exception as e:
        print(f"❌ Error generating {framework} files: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_langgraph_files(agent_info: dict, session_dir: Path):
    """Generate LangGraph agent files with proper database avoidance."""
    
    # Generate main agent file
    agent_code = f'''"""
{agent_info['agent_name']} - {agent_info['description']}
Generated by RunAgent Generator
"""

from typing import List, TypedDict
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

class AgentState(TypedDict):
    query: str
    result: str
    input_data: dict

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

def process_agent(state: AgentState) -> AgentState:
    """Main processing function for {agent_info['agent_name']}"""
    
    query = state['query']
    input_data = state.get('input_data', {{}})
    
    prompt = f"""
    {agent_info['description']}
    
    User query: {{query}}
    Input data: {{input_data}}
    
    Please provide a helpful response based on the functionality: {agent_info['main_functionality']}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {{**state, "result": response.content}}

def create_workflow():
    """Create the agent workflow"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("process", process_agent)
    workflow.set_entry_point("process") 
    workflow.add_edge("process", END)
    
    return workflow.compile()

# Create workflow
app = create_workflow()

def main(*input_args, **input_kwargs):
    """Main entry point for RunAgent (standard)"""
    
    # Extract query and input data
    query = input_kwargs.get("query", "")
    if not query and input_args:
        query = str(input_args[0])
    
    # Handle different input field names
    for field in {agent_info['input_fields']}:
        if field in input_kwargs:
            query = str(input_kwargs[field])
            break
    
    if not query:
        query = "Hello, how can I help you?"
    
    # Run the workflow
    result = app.invoke({{
        "query": query,
        "input_data": input_kwargs,
        "result": ""
    }})
    
    return result["result"]

def main_stream(*input_args, **input_kwargs):
    """Streaming entry point"""
    query = input_kwargs.get("query", "")
    if not query and input_args:
        query = str(input_args[0])
    
    # Handle different input field names
    for field in {agent_info['input_fields']}:
        if field in input_kwargs:
            query = str(input_kwargs[field])
            break
    
    if not query:
        query = "Hello, how can I help you?"
    
    # Stream the workflow execution
    try:
        for chunk in app.stream({{
            "query": query,
            "input_data": input_kwargs,
            "result": ""
        }}):
            yield str(chunk)
    except Exception as e:
        yield f"Error: {{str(e)}}"
'''
    
    # Write agent file
    with open(session_dir / "agent.py", "w") as f:
        f.write(agent_code)
    
    # Generate requirements.txt
    requirements = """langgraph>=0.0.65
langchain>=0.1.0
langchain-core>=0.1.0
langchain-openai>=0.0.5
"""
    
    with open(session_dir / "requirements.txt", "w") as f:
        f.write(requirements)
    
    # Generate runagent.config.json
    config = {
        "agent_name": agent_info['agent_name'],
        "description": agent_info['description'],
        "framework": "langgraph",
        "template": "custom",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "template_source": {
            "repo_url": "https://github.com/runagent-dev/runagent.git",
            "path": "generated/custom",
            "author": "runagent-generator"
        },
        "agent_architecture": {
            "entrypoints": [
                {
                    "file": "agent.py",
                    "module": "main",
                    "tag": "main"
                },
                {
                    "file": "agent.py", 
                    "module": "main_stream",
                    "tag": "main_stream"
                }
            ]
        },
        "input_fields": agent_info['input_fields']
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Generated LangGraph config:")
    print(json.dumps(config, indent=2))

def generate_letta_files(agent_info: dict, session_dir: Path):
    """Generate Letta agent files."""
    
    agent_code = f'''import os
from typing import Any
from dotenv import load_dotenv
from letta_client import CreateBlock, Letta

load_dotenv()

def _extract_message_from_input(*input_args, **input_kwargs) -> str:
    """Extract message from various input formats"""
    
    # Try different input field names
    for field in {agent_info['input_fields']}:
        if input_kwargs.get(field):
            return str(input_kwargs[field])
    
    # Try first positional argument
    if input_args and isinstance(input_args[0], str):
        return input_args[0]
    
    return "No input provided"

def letta_run(*input_args, **input_kwargs):
    """Main Letta agent function"""
    try:
        client = Letta(base_url="http://localhost:8283")
        
        # Create memory blocks
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are interacting with a user through RunAgent framework",
            ),
            CreateBlock(
                label="persona", 
                value="{agent_info['description']}. Be helpful and focused on: {agent_info['main_functionality']}",
            ),
        ]

        # Create agent
        agent = client.agents.create(
            name=f"runagent-{agent_info['agent_name']}-{{os.getpid()}}",
            memory_blocks=memory_blocks,
            system="{agent_info['description']} Focus on: {agent_info['main_functionality']}",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            include_base_tools=True
        )

        # Extract message from input
        message = _extract_message_from_input(*input_args, **input_kwargs)
        
        # Send message to agent
        response = client.agents.messages.create(
            agent_id=agent.id,
            messages=[{{"role": "user", "content": message}}]
        )

        return response
        
    except Exception as e:
        return f"Letta execution error: {{str(e)}}"

def letta_run_stream(*input_args, **input_kwargs):
    """Streaming Letta function"""
    try:
        client = Letta(base_url="http://localhost:8283")
        
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are interacting with a user through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="{agent_info['description']}. Be helpful and focused on: {agent_info['main_functionality']}",
            ),
        ]

        agent = client.agents.create(
            name=f"runagent-{agent_info['agent_name']}-stream-{{os.getpid()}}",
            memory_blocks=memory_blocks,
            system="{agent_info['description']} Focus on: {agent_info['main_functionality']}",
            model="openai/gpt-4o-mini", 
            embedding="openai/text-embedding-ada-002",
            include_base_tools=True
        )

        message = _extract_message_from_input(*input_args, **input_kwargs)
        
        stream = client.agents.messages.create_stream(
            agent_id=agent.id,
            messages=[{{"role": "user", "content": message}}],
            stream_tokens=True,
        )
        
        for chunk in stream:
            yield chunk
            
    except Exception as e:
        yield f"Letta streaming error: {{str(e)}}"
'''
    
    with open(session_dir / "agent.py", "w") as f:
        f.write(agent_code)
    
    # Generate config
    config = {
        "agent_name": agent_info['agent_name'],
        "description": agent_info['description'],
        "framework": "letta",
        "template": "custom",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "template_source": {
            "repo_url": "https://github.com/runagent-dev/runagent.git",
            "path": "generated/custom",
            "author": "runagent-generator"
        },
        "agent_architecture": {
            "entrypoints": [
                {
                    "file": "agent.py",
                    "module": "letta_run", 
                    "tag": "main"
                },
                {
                    "file": "agent.py",
                    "module": "letta_run_stream",
                    "tag": "main_stream"
                }
            ]
        },
        "input_fields": agent_info['input_fields'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}",
            "LETTA_SERVER_URL": "http://localhost:8283"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def generate_agno_files(agent_info: dict, session_dir: Path):
    """Generate Agno agent files."""
    
    agent_code = f'''from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description="{agent_info['description']}",
    instructions="Focus on: {agent_info['main_functionality']}",
    markdown=True
)

def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    prompt = ""
    for field in {agent_info['input_fields']}:
        if input_kwargs.get(field):
            prompt = str(input_kwargs[field])
            break
    
    if not prompt and input_args:
        prompt = str(input_args[0])
    
    if not prompt:
        prompt = "Hello, how can I help you?"
    
    # Add context about the agent's purpose
    full_prompt = f"""
    {agent_info['description']}
    
    User request: {{prompt}}
    
    Please provide a helpful response focused on: {agent_info['main_functionality']}
    """
    
    response = agent.run(full_prompt)
    
    return {{
        "content": response.content if hasattr(response, 'content') else str(response),
    }}

def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    prompt = ""
    for field in {agent_info['input_fields']}:
        if input_kwargs.get(field):
            prompt = str(input_kwargs[field])
            break
    
    if not prompt and input_args:
        prompt = str(input_args[0])
    
    full_prompt = f"""
    {agent_info['description']}
    
    User request: {{prompt}}
    
    Please provide a helpful response focused on: {agent_info['main_functionality']}
    """
    
    for chunk in agent.run(full_prompt, stream=True):
        yield {{
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }}

# Keep original functions for backward compatibility  
agent_run_stream = partial(agent.run, stream=True)
'''
    
    with open(session_dir / "agent.py", "w") as f:
        f.write(agent_code)
    
    # Generate requirements
    with open(session_dir / "requirements.txt", "w") as f:
        f.write("agno>=1.7.2\n")
    
    # Generate config
    config = {
        "agent_name": agent_info['agent_name'],
        "description": agent_info['description'],
        "framework": "agno",
        "template": "custom",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent_architecture": {
            "entrypoints": [
                {
                    "file": "agent.py",
                    "module": "agent_run",
                    "tag": "main",
                    "extractor": {{"content": "$.content"}}
                },
                {
                    "file": "agent.py",
                    "module": "agent_run_stream", 
                    "tag": "main_stream",
                    "extractor": {{"content": "$.content"}}
                }
            ]
        },
        "input_fields": agent_info['input_fields']
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def generate_llamaindex_files(agent_info: dict, session_dir: Path):
    """Generate LlamaIndex agent files."""
    
    agent_code = f'''from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

# Initialize LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.3)

# Create the agent
agent = FunctionAgent(
    tools=[],  # Add tools as needed
    llm=llm,
    system_prompt="{agent_info['description']} Focus on: {agent_info['main_functionality']}"
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    user_input = ""
    for field in {agent_info['input_fields']}:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    if not user_input:
        user_input = "Hello, how can I help you?"
    
    response = await agent.run(user_input)
    return response

async def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    user_input = ""
    for field in {agent_info['input_fields']}:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        yield event
'''
    
    with open(session_dir / "agent.py", "w") as f:
        f.write(agent_code)
    
    # Generate requirements
    with open(session_dir / "requirements.txt", "w") as f:
        f.write("llama-index>=0.12.48\n")
    
    # Generate config
    config = {
        "agent_name": agent_info['agent_name'],
        "description": agent_info['description'],
        "framework": "llamaindex",
        "template": "custom",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent_architecture": {
            "entrypoints": [
                {
                    "file": "agent.py",
                    "module": "agent_run",
                    "tag": "main"
                },
                {
                    "file": "agent.py",
                    "module": "agent_run_stream",
                    "tag": "main_stream"
                }
            ]
        },
        "input_fields": agent_info['input_fields']
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

# In your main.py, modify the start_runagent_server function:

def start_runagent_server(session_dir: str, session_id: str):
    """Start runagent server for the generated agent."""
    
    try:
        print(f"🚀 Starting RunAgent server for session: {session_id}")
        
        # Find available port
        import socket
        def find_free_port(start_port=8080):
            for port in range(start_port, start_port + 100):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(('localhost', port))
                        return port
                    except OSError:
                        continue
            raise Exception("No free ports available")
        
        port = find_free_port()
        print(f"🔌 Using port: {port}")
        
        # Install dependencies
        print("📦 Installing agent dependencies...")
        try:
            result = subprocess.run(["pip", "install", "-r", "requirements.txt"], 
                                  cwd=session_dir, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
            else:
                print(f"⚠️ Dependency installation warning: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Dependency installation failed: {e}")
        
        # Set up environment to bypass database issues
        env = os.environ.copy()
        env['RUNAGENT_DISABLE_DB'] = 'true'
        env['RUNAGENT_LOG_LEVEL'] = 'INFO'
        
        # Start RunAgent server with simple command
        cmd = ["runagent", "serve", ".", "--host", "0.0.0.0", "--port", str(port)]
        
        print(f"🔧 Running command: {' '.join(cmd)}")
        print(f"📂 Working directory: {session_dir}")
        
        process = subprocess.Popen(
            cmd,
            cwd=session_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env
        )
        
        # Wait for server to start
        agent_id = str(uuid.uuid4())
        start_time = time.time()
        timeout = 60
        
        print("📡 Waiting for RunAgent server to start...")
        
        server_started = False
        while time.time() - start_time < timeout:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"❌ RunAgent process exited early:")
                print(f"OUTPUT: {stdout}")
                break
            
            try:
                line = process.stdout.readline()
                if line:
                    print(f"RunAgent: {line.strip()}")
                    
                    # Look for server startup indicators
                    if any(keyword in line.lower() for keyword in ["server running", "uvicorn running", "started server", "listening on"]):
                        server_started = True
                        print(f"✅ Server startup detected!")
                        break
                        
            except Exception as e:
                print(f"Error reading output: {e}")
                pass
            
            time.sleep(0.5)
        
        # Test server health
        if server_started:
            for attempt in range(5):
                try:
                    import requests
                    test_url = f"http://localhost:{port}/health"
                    response = requests.get(test_url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ Server health check passed!")
                        break
                except Exception as e:
                    print(f"⚠️ Health check attempt {attempt + 1} failed: {e}")
                    time.sleep(2)
        
        agent_url = f"http://localhost:8000/static/agent.html?agent={agent_id}"
        
        # Store running agent info
        running_agents[session_id] = {
            "process": process,
            "agent_id": agent_id,
            "agent_url": agent_url,
            "port": port,
            "runagent_url": f"http://localhost:{port}"
        }
        
        print(f"🎉 RunAgent server started successfully!")
        print(f"🔗 Agent ID: {agent_id}")
        print(f"🌐 RunAgent URL: http://localhost:{port}")
        print(f"🖥️  UI URL: {agent_url}")
        
        return agent_id, agent_url, port
        
    except Exception as e:
        print(f"❌ Error starting agent server: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for agent generation."""
    
    session_id = request.session_id or str(uuid.uuid4())
    message = request.message.strip()
    
    # Debug logging
    print(f"🔍 Received message: '{request.message}' (processed: '{message}')")
    print(f"🆔 Session ID: {session_id}")
    
    # Get or create session
    if session_id not in sessions:
        sessions[session_id] = {
            "stage": "understanding",
            "messages": [],
            "agent_info": None,
            "files_generated": False
        }
    
    session = sessions[session_id]
    print(f"📊 Current stage: {session['stage']}")
    
    session["messages"].append({"role": "user", "content": request.message})
    
    try:
        # Stage 1: Understanding the request
        if session["stage"] == "understanding":
            print("🧠 Analyzing user request with GPT-5...")
            agent_info = analyze_user_request(request.message)
            session["agent_info"] = agent_info
            session["stage"] = "planning"
            
            description = f"""I understand you want to create: **{agent_info['agent_name']}**

**Framework:** {agent_info['framework']}
**Description:** {agent_info['description']}
**Main Functionality:** {agent_info['main_functionality']}
**Input Fields:** {', '.join(agent_info['input_fields'])}

Let me create a workflow diagram for this agent..."""

            print("🎨 Generating dynamic Mermaid diagram with GPT-5...")
            try:
                mermaid_diagram = generate_mermaid_diagram(agent_info)
                
                # Validate the generated diagram
                is_valid, validation_message = validate_mermaid_syntax(mermaid_diagram)
                if not is_valid:
                    print(f"⚠️ Generated diagram validation failed: {validation_message}")
                    print(f"🔧 Attempting to fix diagram...")
                    
                    # Try simple fixes
                    if "Missing graph declaration" in validation_message:
                        mermaid_diagram = f"graph TD\n    {mermaid_diagram}"
                    
                    # Re-validate
                    is_valid, _ = validate_mermaid_syntax(mermaid_diagram)
                
                if is_valid:
                    print("✅ Mermaid diagram generated and validated successfully")
                else:
                    print("❌ Could not generate valid Mermaid diagram")
                    
            except Exception as e:
                print(f"❌ Mermaid generation failed: {e}")
                # Don't fail the entire request - the frontend will show the error
                mermaid_diagram = None
            
            return ChatResponse(
                response=description,
                session_id=session_id,
                stage="planning",
                description=agent_info['description'],
                mermaid_diagram=mermaid_diagram
            )
        
        # Stage 2: Planning - handle user feedback/modifications
        elif session["stage"] == "planning":
            if any(phrase in message.lower() for phrase in ["go for it", "generate", "create it", "build it", "make it", "proceed", "continue", "yes", "start"]):
                print(f"🚀 Starting agent generation for session {session_id}")
                
                # Generate agent files
                print("📁 Generating agent files...")
                success = generate_agent_files(session["agent_info"], session_id)
                
                if not success:
                    raise Exception("Failed to generate agent files")
                
                print(f"✅ Files generated successfully for session {session_id}")
                session["files_generated"] = True
                session["stage"] = "starting"
                
                # Start RunAgent server immediately in background
                session_dir_path = Path(f"generated_agents/{session_id}")
                
                def start_agent():
                    print(f"🚀 Background task: Starting agent for session {session_id}")
                    try:
                        agent_id, agent_url, port = start_runagent_server(str(session_dir_path), session_id)
                        
                        if agent_id and agent_url:
                            session["agent_id"] = agent_id
                            session["agent_url"] = agent_url
                            session["runagent_port"] = port
                            session["stage"] = "complete"
                            
                            # Store agent info for the agent UI to access
                            running_agents[agent_id] = {
                                "agent_info": session["agent_info"],
                                "session_id": session_id,
                                "status": "active",
                                "port": port,
                                "runagent_url": f"http://localhost:{port}"
                            }
                            print(f"✅ Agent {agent_id} is now ready at port {port}!")
                        else:
                            session["stage"] = "error"
                            session["error"] = "Failed to start RunAgent server"
                            print(f"❌ Failed to start agent for session {session_id}")
                    except Exception as e:
                        print(f"❌ Error in background agent start: {e}")
                        session["stage"] = "error"
                        session["error"] = str(e)
                
                # Start the agent server in background
                print(f"🔄 Starting background thread for session {session_id}")
                threading.Thread(target=start_agent, daemon=True).start()
                
                return ChatResponse(
                    response=f"""✅ Agent files generated successfully! Now starting the RunAgent server...

🔄 Starting your **{session["agent_info"]["agent_name"]}** agent server...

This involves:
1. Installing {session["agent_info"]["framework"]} dependencies
2. Starting RunAgent server on available port
3. Initializing your agent

⏳ Please wait 30-90 seconds, then **send any message** (like "status") to check if it's ready.""",
                    session_id=session_id,
                    stage="starting"
                )
            else:
                # Handle modifications
                return ChatResponse(
                    response="I can help you modify the agent. What would you like to change? Or say 'go for it' or 'generate' to proceed with the current design.",
                    session_id=session_id,
                    stage="planning",
                    description=session["agent_info"]["description"],
                    mermaid_diagram=generate_mermaid_diagram(session["agent_info"])
                )
        
        # Stage 3: Check agent status or continue if starting
        elif session["stage"] == "starting":
            print(f"📊 Checking status for starting session {session_id}")
            
            # Check if agent has been started in the background
            if session.get("agent_id") and session.get("agent_url"):
                # Agent is ready!
                session["stage"] = "complete"
                agent_id = session["agent_id"]
                agent_url = session["agent_url"]
                runagent_port = session.get("runagent_port")
                
                return ChatResponse(
                    response=f"""🎉 Your **{session["agent_info"]["agent_name"]}** is now ready!

**Agent ID:** `{agent_id}`

**🚀 Click here to use your agent:**
{agent_url}

**RunAgent Server:** `http://localhost:{runagent_port}`

Your {session["agent_info"]["framework"]} agent is running and ready to process real requests!

The agent interface connects directly to your RunAgent server for authentic responses.""",
                    session_id=session_id,
                    stage="complete",
                    agent_id=agent_id,
                    agent_url=agent_url
                )
            elif session.get("stage") == "error":
                error_msg = session.get("error", "Unknown error occurred")
                print(f"❌ Error in session {session_id}: {error_msg}")
                return ChatResponse(
                    response=f"❌ Error starting agent: {error_msg}\n\nPlease try again or check the server logs.",
                    session_id=session_id,
                    stage="error"
                )
            else:
                # Still starting
                return ChatResponse(
                    response="""⏳ Still starting your agent server... 

The process includes:
- Installing dependencies (this can take time for first install)
- Initializing the RunAgent framework
- Starting the server and verifying connectivity

Please wait a bit longer and send another message to check status.

If it takes more than 3-4 minutes, there might be an issue with dependencies or port conflicts.""",
                    session_id=session_id,
                    stage="starting"
                )
        
        # Agent is complete or checking status
        else:
            if session["stage"] == "complete":
                agent_id = session.get("agent_id")
                agent_url = session.get("agent_url") 
                runagent_port = session.get("runagent_port")
                
                return ChatResponse(
                    response=f"""🎉 Your **{session["agent_info"]["agent_name"]}** is ready!

**Agent ID:** `{agent_id}`

**🚀 Click here to use your agent:**
{agent_url}

**RunAgent Server:** `http://localhost:{runagent_port}` 

Your {session["agent_info"]["framework"]} agent is running and will provide real responses based on your framework choice!

The agent interface connects directly to your RunAgent server for authentic responses.""",
                    session_id=session_id,
                    stage="complete",
                    agent_id=agent_id,
                    agent_url=agent_url
                )
            elif session["stage"] == "starting":
                return ChatResponse(
                    response="⏳ Still starting your agent server... Please wait a bit longer and try again.",
                    session_id=session_id,
                    stage="starting"
                )
            elif session["stage"] == "error":
                error_msg = session.get("error", "Unknown error")
                return ChatResponse(
                    response=f"❌ Error: {error_msg}\n\nYou can try starting over by describing a new agent.",
                    session_id=session_id,
                    stage="error"
                )
            else:
                return ChatResponse(
                    response=f"Your agent status: {session.get('stage', 'unknown')}. How can I help you?",
                    session_id=session_id,
                    stage=session.get("stage", "understanding")
                )
    
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return ChatResponse(
            response=f"Sorry, I encountered an error: {str(e)}\n\nPlease check the server logs and try again.",
            session_id=session_id,
            stage="error"
        )

@app.get("/debug/agent-logs/{agent_id}")
async def get_agent_logs(agent_id: str):
    """Get logs for a specific agent to help with debugging."""
    
    # Check in running_agents first
    if agent_id in running_agents:
        agent_data = running_agents[agent_id]
        if "process" in agent_data and agent_data["process"]:
            process = agent_data["process"]
            return {
                "agent_id": agent_id,
                "status": "running" if process.poll() is None else "stopped",
                "port": agent_data.get("port"),
                "session_id": agent_data.get("session_id")
            }
    
    # Find session with this agent_id
    for session_id, session in sessions.items():
        if session.get("agent_id") == agent_id:
            return {
                "agent_id": agent_id,
                "session_id": session_id,
                "stage": session.get("stage"),
                "agent_info": session.get("agent_info"),
                "error": session.get("error")
            }
    
    raise HTTPException(status_code=404, detail="Agent not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_sessions": len(sessions)}

@app.get("/debug/test-runagent/{agent_id}")
async def test_runagent_connection(agent_id: str):
    """Test connection to a running RunAgent server."""
    import requests
    
    # Find the agent's port
    port = None
    if agent_id in running_agents:
        port = running_agents[agent_id].get("port")
    else:
        # Check sessions
        for session_id, session in sessions.items():
            if session.get("agent_id") == agent_id:
                port = session.get("runagent_port")
                break
    
    if not port:
        return {"error": "Agent not found or port not available"}
    
    base_url = f"http://localhost:{port}"
    
    # Test various endpoints
    results = {}
    
    test_endpoints = [
        "/",
        "/health", 
        "/docs",
        "/run",
        "/agents",
        "/agents/main/run"
    ]
    
    for endpoint in test_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            results[endpoint] = {
                "status": response.status_code,
                "accessible": True,
                "content_type": response.headers.get("content-type", ""),
                "content_preview": response.text[:200] if response.text else ""
            }
        except Exception as e:
            results[endpoint] = {
                "status": "error",
                "accessible": False,
                "error": str(e)
            }
    
    return {
        "agent_id": agent_id,
        "port": port,
        "base_url": base_url,
        "endpoints": results
    }

@app.get("/debug/clear-sessions")
async def clear_sessions():
    """Clear all sessions and running agents for debugging."""
    global sessions, running_agents
    
    # Stop any running processes
    for session_id, agent_data in running_agents.items():
        if "process" in agent_data and agent_data["process"]:
            try:
                agent_data["process"].terminate()
                print(f"🛑 Terminated process for session {session_id}")
            except:
                pass
    
    sessions.clear()
    running_agents.clear()
    
    return {"message": "All sessions and agents cleared", "status": "success"}

if __name__ == "__main__":
    import uvicorn
    
    # Create directories
    os.makedirs("generated_agents", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)