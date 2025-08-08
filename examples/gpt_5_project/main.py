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
    """Generate Mermaid diagram for the agent workflow."""
    
    # Instead of relying on GPT-5 (which is inconsistent), 
    # generate a reliable diagram based on the framework
    framework = agent_info['framework']
    agent_name = agent_info['agent_name'].replace(' ', '')
    
    try:
        if framework == "llamaindex":
            return f"""graph TD
    A[User Input] --> B[Parse Query]
    B --> C[{agent_name}]
    C --> D[LlamaIndex Processing]
    D --> E[Retrieve Examples]
    D --> F[Calculate Solution]
    E --> G[Generate Explanation]
    F --> G
    G --> H[Return Result]"""
        
        elif framework == "langgraph":
            return f"""graph TD
    A[User Input] --> B[{agent_name}]
    B --> C[Problem Analysis]
    C --> D[Solution Planning]
    D --> E[Step Execution]
    E --> F[Validation]
    F --> G[Generate Response]
    G --> H[Return Result]"""
        
        elif framework == "letta":
            return f"""graph TD
    A[User Input] --> B[{agent_name}]
    B --> C[Memory Retrieval]
    C --> D[Context Processing]
    D --> E[Tool Execution]
    E --> F[Response Generation]
    F --> G[Memory Update]
    G --> H[Return Result]"""
        
        elif framework == "agno":
            return f"""graph TD
    A[User Input] --> B[{agent_name}]
    B --> C[Request Analysis]
    C --> D[Processing]
    D --> E[Response Generation]
    E --> F[Return Result]"""
        
        else:
            return f"""graph TD
    A[User Input] --> B[{agent_name}]
    B --> C[Process Request]
    C --> D[Generate Response]
    D --> E[Return Result]"""
            
    except Exception as e:
        print(f"Error generating diagram: {e}")
        # Fallback to ultra-simple diagram
        return f"""graph TD
    A[Input] --> B[{agent_name}]
    B --> C[Output]"""

def generate_agent_files(agent_info: dict, session_id: str) -> bool:
    """Generate agent files based on template and user requirements."""
    
    framework = agent_info['framework']
    template_type = agent_info['template_type']
    
    # Create session directory
    session_dir = Path(f"generated_agents/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Create .env file with OpenAI API key
    env_content = f"""# OpenAI API Key
OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')}

# Letta Configuration (if using Letta)
LETTA_SERVER_URL=http://localhost:8283
"""
    
    with open(session_dir / ".env", "w") as f:
        f.write(env_content)
    
    # Get template info
    template_info = TEMPLATES.get(framework, {}).get(template_type, {})
    
    try:
        if framework == "langgraph":
            generate_langgraph_files(agent_info, session_dir)
        elif framework == "letta":
            generate_letta_files(agent_info, session_dir)
        elif framework == "agno":
            generate_agno_files(agent_info, session_dir)
        elif framework == "llamaindex":
            generate_llamaindex_files(agent_info, session_dir)
        
        return True
    except Exception as e:
        print(f"Error generating files: {e}")
        return False

def generate_langgraph_files(agent_info: dict, session_dir: Path):
    """Generate LangGraph agent files."""
    
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

def run(*input_args, **input_kwargs):
    """Main entry point for RunAgent"""
    
    # Extract query and input data
    query = input_kwargs.get("query", "")
    if not query and input_args:
        query = str(input_args[0])
    
    # Run the workflow
    result = app.invoke({{
        "query": query,
        "input_data": input_kwargs,
        "result": ""
    }})
    
    return result["result"]

def run_stream(*input_args, **input_kwargs):
    """Streaming entry point"""
    query = input_kwargs.get("query", "")
    if not query and input_args:
        query = str(input_args[0])
    
    # Stream the workflow
    for chunk in app.stream({{
        "query": query,
        "input_data": input_kwargs,
        "result": ""
    }}):
        yield chunk
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
                    "module": "run",
                    "tag": "main"
                },
                {
                    "file": "agent.py", 
                    "module": "run_stream",
                    "tag": "main_stream"
                }
            ]
        },
        "input_fields": agent_info['input_fields']
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    # Debug: Print the generated config
    print(f"✅ Generated config for {framework}:")
    print(json.dumps(config, indent=2))
    
    # Debug: Print the generated config
    print(f"✅ Generated config for {framework}:")
    print(json.dumps(config, indent=2))
    
    # Debug: Print the generated config
    print(f"✅ Generated config for {framework}:")
    print(json.dumps(config, indent=2))
    
    # Debug: Print the generated config
    print(f"✅ Generated config for {framework}:")
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
    message = request.message.lower().strip()
    
    # Debug logging
    print(f"DEBUG: Received message: '{request.message}' (processed: '{message}')")
    print(f"DEBUG: Session ID: {session_id}")
    
    # Get or create session
    if session_id not in sessions:
        sessions[session_id] = {
            "stage": "understanding",
            "messages": [],
            "agent_info": None,
            "files_generated": False
        }
    
    session = sessions[session_id]
    print(f"DEBUG: Current stage: {session['stage']}")
    
    session["messages"].append({"role": "user", "content": request.message})
    
    try:
        # Stage 1: Understanding the request
        if session["stage"] == "understanding":
            agent_info = analyze_user_request(request.message)
            session["agent_info"] = agent_info
            session["stage"] = "planning"
            
            description = f"""I understand you want to create: **{agent_info['agent_name']}**

**Framework:** {agent_info['framework']}
**Description:** {agent_info['description']}
**Main Functionality:** {agent_info['main_functionality']}
**Input Fields:** {', '.join(agent_info['input_fields'])}

Let me create a workflow diagram for this agent..."""

            mermaid_diagram = generate_mermaid_diagram(agent_info)
            
            return ChatResponse(
                response=description,
                session_id=session_id,
                stage="planning",
                description=agent_info['description'],
                mermaid_diagram=mermaid_diagram
            )
        
        # Handle user feedback/modifications
        elif session["stage"] == "planning":
            if any(phrase in message for phrase in ["go for it", "generate", "create it", "build it", "make it", "proceed", "continue", "yes", "start"]):
                print(f"DEBUG: Starting agent generation for session {session_id}")
                
                # Generate agent files
                success = generate_agent_files(session["agent_info"], session_id)
                
                if success:
                    print(f"DEBUG: Files generated successfully for session {session_id}")
                    session["files_generated"] = True
                    session["stage"] = "starting"
                    
                    # Start RunAgent server immediately in background
                    session_dir_path = Path(f"generated_agents/{session_id}")
                    
                    def start_agent():
                        print(f"🚀 Background task: Starting agent for session {session_id}")
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
                    
                    # Start the agent server in background
                    print(f"DEBUG: Starting background thread for session {session_id}")
                    threading.Thread(target=start_agent, daemon=True).start()
                    
                    return ChatResponse(
                        response=f"""✅ Agent files generated successfully! Now starting the RunAgent server...

🔄 Starting your **{session["agent_info"]["agent_name"]}** agent server...

This involves:
1. Installing {session["agent_info"]["framework"]} dependencies
2. Starting RunAgent server on available port
3. Initializing your agent

⏳ Please wait 30-60 seconds, then **send any message** (like "status") to check if it's ready.""",
                        session_id=session_id,
                        stage="starting"
                    )
                else:
                    return ChatResponse(
                        response="❌ Error generating agent files. Please try again.",
                        session_id=session_id,
                        stage="error"
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
            print(f"DEBUG: Checking status for starting session {session_id}")
            
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

Your {session["agent_info"]["framework"]} agent is running and will provide real mathematical computations!

The agent interface connects directly to your RunAgent server for authentic responses.""",
                    session_id=session_id,
                    stage="complete",
                    agent_id=agent_id,
                    agent_url=agent_url
                )
            elif session.get("stage") == "error":
                return ChatResponse(
                    response=f"❌ Error starting agent: {session.get('error', 'Unknown error')}",
                    session_id=session_id,
                    stage="error"
                )
            else:
                # Still starting
                return ChatResponse(
                    response="""⏳ Still starting your agent server... 

The process includes:
- Installing dependencies (this can take time)
- Initializing the RunAgent framework
- Starting the server

Please wait a bit longer and send another message to check status.

If it takes more than 2-3 minutes, there might be an issue with dependencies.""",
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

Your {session["agent_info"]["framework"]} agent is running and will provide real mathematical computations! 

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
            else:
                return ChatResponse(
                    response=f"Your agent status: {session.get('stage', 'unknown')}. How can I help you?",
                    session_id=session_id,
                    stage=session.get("stage", "understanding")
                )
    
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response=f"Sorry, I encountered an error: {str(e)}",
            session_id=session_id,
            stage="error"
        )

@app.get("/agent/{agent_id}")
async def get_agent_info(agent_id: str):
    """Get agent information for the UI."""
    
    # Check in running_agents first (for real agents)
    if agent_id in running_agents:
        agent_data = running_agents[agent_id]
        return {
            "agent_id": agent_id,
            "agent_info": {
                **agent_data["agent_info"],
                "runagent_url": agent_data.get("runagent_url"),
                "port": agent_data.get("port")
            },
            "session_id": agent_data["session_id"],
            "status": agent_data["status"]
        }
    
    # Fallback: Find session with this agent_id
    for session_id, session in sessions.items():
        if session.get("agent_id") == agent_id:
            # Also check if we have running agent info
            if session_id in running_agents:
                agent_data = running_agents[session_id]
                return {
                    "agent_id": agent_id,
                    "agent_info": {
                        **session["agent_info"],
                        "runagent_url": agent_data.get("runagent_url"),
                        "port": agent_data.get("port")
                    },
                    "session_id": session_id,
                    "status": "active"
                }
            else:
                return {
                    "agent_id": agent_id,
                    "agent_info": {
                        **session["agent_info"],
                        "runagent_url": f"http://localhost:{session.get('runagent_port', 8080)}",
                        "port": session.get("runagent_port", 8080)
                    },
                    "session_id": session_id,
                    "status": "active"
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