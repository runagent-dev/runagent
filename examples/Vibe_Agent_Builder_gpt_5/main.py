from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
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
    sdk_config: Optional[dict] = None  # New field for SDK configuration

def analyze_user_request(message: str) -> dict:
    """Use GPT-5 to analyze user request and extract agent requirements."""
    
    prompt = f"""
    Analyze this user request for creating an AI agent: "{message}"
    
    Extract and return a JSON with:
    1. agent_name: A concise name for the agent (snake_case, no spaces)
    2. framework: One of [langgraph, letta, agno, llamaindex] 
    3. template_type: "basic" or "advanced"
    4. description: What the agent does (2-3 sentences)
    5. main_functionality: Primary purpose (concise)
    6. input_fields: List of input field names the agent needs (e.g., ["query", "max_results"])
    7. input_types: Object mapping field names to types (e.g., {{"query": "string", "max_results": "number"}})
    8. input_descriptions: Object mapping field names to descriptions
    9. expected_output_format: Description of what the agent returns
    10. example_inputs: List of example input objects
    11. backend_language: "python" or "typescript" (default python unless specified)
    12. entrypoint_tags: List of entrypoint tags (e.g., ["main", "main_stream"])
    
    Choose framework based on:
    - langgraph: Complex workflows, multi-agent systems, decision trees
    - letta: Conversational AI, memory-based agents, chat interfaces  
    - agno: Simple assistants, analysis tasks, reporting
    - llamaindex: RAG, document processing, knowledge retrieval
    
    Make input_fields specific to the use case. For example:
    - Weather agent: ["location", "units"]
    - Math solver: ["expression", "show_steps"]
    - Research agent: ["topic", "depth", "sources"]
    - Content writer: ["topic", "style", "length"]
    
    Return only valid JSON.
    """
    
    try:
        response = openai_client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            reasoning={"effort": "minimal"}
        )
        
        content = response.output[1].content[0].text
        result = json.loads(content)
        
        # Ensure required fields have defaults
        result.setdefault("input_fields", ["query"])
        result.setdefault("input_types", {"query": "string"})
        result.setdefault("input_descriptions", {"query": "User input"})
        result.setdefault("entrypoint_tags", ["main", "main_stream"])
        result.setdefault("expected_output_format", "String response")
        result.setdefault("example_inputs", [{"query": "Hello, how can you help me?"}])
        
        return result
    except Exception as e:
        print(f"Error analyzing request: {e}")
        return {
            "agent_name": "custom_agent",
            "framework": "agno",
            "template_type": "basic", 
            "description": "A custom AI agent",
            "main_functionality": "General assistance",
            "input_fields": ["query"],
            "input_types": {"query": "string"},
            "input_descriptions": {"query": "User input"},
            "expected_output_format": "String response",
            "example_inputs": [{"query": "Hello"}],
            "entrypoint_tags": ["main", "main_stream"],
            "backend_language": "python"
        }
def generate_agent_test_script(agent_info: dict, session_dir: Path):
    """Generate agent test script with proper buffering support"""
    
    primary_field = agent_info['input_fields'][0] if agent_info['input_fields'] else 'query'
    
    # Create input preparation logic
    input_assignments = [f'    input_data["{primary_field}"] = test_message']
    
    # Add other fields with appropriate defaults
    for field in agent_info['input_fields'][1:]:
        field_type = agent_info['input_types'].get(field, 'string')
        if field_type in ['number', 'integer']:
            default_value = '1'
        elif field_type == 'boolean':
            default_value = 'True'
        elif field_type in ['array', 'list']:
            default_value = '[]'
        else:
            default_value = f'"short"' if 'length' in field else f'"default"'
        
        input_assignments.append(f'    input_data["{field}"] = {default_value}')
    
    input_prep = '\n'.join(input_assignments)
    
    fixed_script = f'''import sys
import time
import json
from runagent import RunAgentClient

def main():
    if len(sys.argv) != 5:
        print("Usage: python3 agent_test.py <agent_id> <host> <port> <test_message>")
        print("Example: python3 agent_test.py abc123 localhost 8450 'Hello'")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    host = sys.argv[2] 
    port = int(sys.argv[3])
    test_message = sys.argv[4]
    
    print(f"Testing Agent: {{agent_id}}")
    print(f"Connection: {{host}}:{{port}}")
    print(f"Test Message: {{test_message}}")
    print(f"Framework: {agent_info['framework']}")
    print("=" * 60)
    
    # Prepare input data based on agent configuration
    input_data = {{}}
{input_prep}
    
    print(f"Prepared inputs for agent: {{json.dumps(input_data, indent=2)}}")
    print(f"Connecting to service at {{host}}:{{port}} ...")
    
    # Test each entrypoint tag in order
    entrypoints = {agent_info['entrypoint_tags']}
    
    for i, tag in enumerate(entrypoints, 1):
        try:
            print(f"\\nAttempt {{i}}/{{len(entrypoints)}}: Testing entrypoint '{{tag}}'")
            start_time = time.time()
            
            # Create RunAgentClient
            ra = RunAgentClient(
                agent_id=agent_id,
                entrypoint_tag=tag,
                local=True
            )
            
            print(f"Client created successfully")
            
            # Test the agent
            if "stream" in tag.lower():
                print("Testing streaming mode:")
                print("-" * 40)
                chunk_count = 0
                
                try:
                    for chunk in ra.run(**input_data):
                        chunk_count += 1
                        print(chunk)
                        
                        if chunk_count > 100:  # Prevent infinite loops
                            print("\\n... [truncated after 100 chunks]")
                            break
                            
                except Exception as stream_error:
                    print(f"\\nStreaming error: {{stream_error}}")
                    continue
                    
                print(f"\\n-" * 40)
                print(f"Received {{chunk_count}} chunks")
            else:
                print("Testing synchronous mode:")
                result = ra.run(**input_data)
                print(f"Result Type: {{type(result)}}")
                print(f"Result Content:")
                if isinstance(result, dict):
                    if 'content' in result:
                        print(result['content'])
                    else:
                        print(json.dumps(result, indent=2, default=str))
                else:
                    result_str = str(result)
                    print(result_str[:500] + "..." if len(result_str) > 500 else result_str)
            
            elapsed = time.time() - start_time
            print(f"\\nExecution Time: {{elapsed:.2f}} seconds")
            print(f"SUCCESS! Agent responded via entrypoint '{{tag}}'")
            sys.exit(0)
            
        except Exception as e:
            print(f"Failed with entrypoint '{{tag}}': {{str(e)}}")
            if i < len(entrypoints):
                print("Trying next entrypoint...")
            continue
    
    print(f"\\nAll {{len(entrypoints)}} entrypoints failed!")
    print("Troubleshooting tips:")
    print("   - Verify the agent is running at the specified host:port")
    print("   - Check that agent_id is correct")
    print("   - Ensure RunAgent is installed: pip install runagent")
    print("   - Try different entrypoint tags manually")
    sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    with open(session_dir / "agent_test.py", "w") as f:
        f.write(fixed_script)
    
    # Make it executable
    import stat
    script_path = session_dir / "agent_test.py"
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    
    print(f"Generated fixed agent test script for {agent_info['agent_name']}")
    print(f"Script location: {script_path}")
    return True


def generate_mermaid_diagram(agent_info: dict) -> str:
    """Generate dynamic Mermaid diagram using GPT-5"""
    
    prompt = f"""
    Create a valid Mermaid flowchart diagram for an AI agent:
    
    Agent Name: {agent_info['agent_name']}
    Framework: {agent_info['framework']}
    Description: {agent_info['description']}
    Main Functionality: {agent_info['main_functionality']}
    Input Fields: {agent_info['input_fields']}
    
    REQUIREMENTS:
    1. Start with "graph TD"
    2. Use simple node IDs (A, B, C, etc.)
    3. Use only basic shapes: [text], {{text}}, ((text))
    4. Use only --> arrows
    5. Keep node text under 20 characters
    6. Maximum 8 nodes total
    7. Show the specific workflow for this agent type
    
    Return ONLY the Mermaid code.
    """
    
    try:
        response = openai_client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            reasoning={"effort": "minimal"}
        )
        
        mermaid_code = response.output[1].content[0].text.strip()
        mermaid_code = mermaid_code.replace('```mermaid', '').replace('```', '').strip()
        
        lines = [line.strip() for line in mermaid_code.split('\n') if line.strip()]
        mermaid_code = '\n    '.join(lines)
        
        if not mermaid_code.startswith(('graph TD', 'graph LR')):
            mermaid_code = f"graph TD\n    {mermaid_code}"
        
        return mermaid_code
        
    except Exception as e:
        print(f"❌ Error generating Mermaid diagram: {e}")
        return f"graph TD\n    A[User Input] --> B[{agent_info['framework']} Processing]\n    B --> C[Generate Response]\n    C --> D[Return Result]"


def generate_langgraph_files(agent_info: dict, session_dir: Path):
    """Generate LangGraph agent files with proper input handling."""
    
    input_fields_str = json.dumps(agent_info['input_fields'])
    input_types_str = json.dumps(agent_info['input_types'])
    
    agent_code = f'''"""
{agent_info['agent_name']} - {agent_info['description']}
Generated by RunAgent Generator
"""

from typing import List, TypedDict, Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

class AgentState(TypedDict):
    input_data: dict
    result: str

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

def process_agent(state: AgentState) -> AgentState:
    """Main processing function for {agent_info['agent_name']}"""
    
    input_data = state.get('input_data', {{}})
    
    # Extract relevant inputs
    extracted_info = []
    for field in {input_fields_str}:
        if field in input_data:
            extracted_info.append(f"{{field}}: {{input_data[field]}}")
    
    input_summary = "\\n".join(extracted_info) if extracted_info else "No specific input provided"
    
    prompt = f"""
    {agent_info['description']}
    
    Main functionality: {agent_info['main_functionality']}
    
    User input:
    {{input_summary}}
    
    Please provide a helpful response based on this agent's purpose.
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
    
    # Run the workflow
    result = app.invoke({{
        "input_data": input_kwargs,
        "result": ""
    }})
    
    return result["result"]

def main_stream(*input_args, **input_kwargs):
    """Streaming entry point"""
    
    try:
        for chunk in app.stream({{
            "input_data": input_kwargs,
            "result": ""
        }}):
            if "result" in chunk.get("process", {{}}):
                yield chunk["process"]["result"]
            else:
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
        "input_types": agent_info['input_types'],
        "input_descriptions": agent_info['input_descriptions'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def generate_agno_files(agent_info: dict, session_dir: Path):
    """Generate Agno agent files with proper input handling."""
    
    input_fields_str = json.dumps(agent_info['input_fields'])
    
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
    input_parts = []
    for field in {input_fields_str}:
        if input_kwargs.get(field):
            input_parts.append(f"{{field}}: {{input_kwargs[field]}}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {{str(input_args[0])}}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\\n".join(input_parts)
    
    # Add context about the agent's purpose
    full_prompt = f"""
    {agent_info['description']}
    
    User input:
    {{user_input}}
    
    Please provide a helpful response focused on: {agent_info['main_functionality']}
    """
    
    response = agent.run(full_prompt)
    
    return {{
        "content": response.content if hasattr(response, 'content') else str(response),
    }}

def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    input_parts = []
    for field in {input_fields_str}:
        if input_kwargs.get(field):
            input_parts.append(f"{{field}}: {{input_kwargs[field]}}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {{str(input_args[0])}}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\\n".join(input_parts)
    
    full_prompt = f"""
    {agent_info['description']}
    
    User input:
    {{user_input}}
    
    Please provide a helpful response focused on: {agent_info['main_functionality']}
    """
    
    for chunk in agent.run(full_prompt, stream=True):
        yield {{
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }}
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
        "template_source": {
            "repo_url": "https://github.com/runagent-dev/runagent.git",
            "path": "generated/custom",
            "author": "runagent-generator",
            "version": "1.0.0"
        },
        "agent_architecture": {
            "entrypoints": [
                {
                    "file": "agent.py",
                    "module": "agent_run",
                    "tag": "main",
                    "extractor": {"content": "$.content"}
                },
                {
                    "file": "agent.py",
                    "module": "agent_run_stream", 
                    "tag": "main_stream",
                    "extractor": {"content": "$.content"}
                }
            ]
        },
        "input_fields": agent_info['input_fields'],
        "input_types": agent_info['input_types'],
        "input_descriptions": agent_info['input_descriptions'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def generate_letta_files(agent_info: dict, session_dir: Path):
    """Generate Letta agent files with proper input handling."""
    
    input_fields_str = json.dumps(agent_info['input_fields'])
    
    agent_code = f'''import os
from typing import Any
from dotenv import load_dotenv
from letta_client import CreateBlock, Letta

load_dotenv()

def _extract_message_from_input(*input_args, **input_kwargs) -> str:
    """Extract message from various input formats"""
    
    # Try different input field names
    input_parts = []
    for field in {input_fields_str}:
        if input_kwargs.get(field):
            input_parts.append(f"{{field}}: {{input_kwargs[field]}}")
    
    if not input_parts and input_args and isinstance(input_args[0], str):
        input_parts.append(f"Input: {{input_args[0]}}")
    
    return "\\n".join(input_parts) if input_parts else "No input provided"

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
    
    # Generate requirements
    with open(session_dir / "requirements.txt", "w") as f:
        f.write("letta-client>=0.1.0\npython-dotenv>=1.0.0\n")
    
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
            "author": "runagent-generator",
            "version": "1.0.0"
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
        "input_types": agent_info['input_types'],
        "input_descriptions": agent_info['input_descriptions'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}",
            "LETTA_SERVER_URL": "http://localhost:8283"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def generate_llamaindex_files(agent_info: dict, session_dir: Path):
    """Generate LlamaIndex agent files with proper input handling."""
    
    input_fields_str = json.dumps(agent_info['input_fields'])
    
    agent_code = f'''from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.agent.workflow import FunctionAgent

# Define a simple tool based on agent functionality
def process_request(query: str) -> str:
    """Process user request based on agent functionality."""
    return f"Processing: {{query}} for {agent_info['main_functionality']}"

# Create an agent workflow
agent = FunctionAgent(
    tools=[process_request],
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="{agent_info['description']} Focus on: {agent_info['main_functionality']}",
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    input_parts = []
    for field in {input_fields_str}:
        if input_kwargs.get(field):
            input_parts.append(f"{{field}}: {{input_kwargs[field]}}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {{str(input_args[0])}}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\\n".join(input_parts)
    
    response = await agent.run(user_input)
    return response

async def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    input_parts = []
    for field in {input_fields_str}:
        if input_kwargs.get(field):
            input_parts.append(f"{{field}}: {{input_kwargs[field]}}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {{str(input_args[0])}}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\\n".join(input_parts)
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        if isinstance(event, AgentStream):
            yield event
        else:
            yield str(event)
'''
    
    with open(session_dir / "agent.py", "w") as f:
        f.write(agent_code)
    
    # Generate requirements
    with open(session_dir / "requirements.txt", "w") as f:
        f.write("llama-index>=0.12.48\nllama-index-llms-openai>=0.3.0\n")
    
    # Generate config
    config = {
        "agent_name": agent_info['agent_name'],
        "description": agent_info['description'],
        "framework": "llamaindex",
        "template": "custom",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "template_source": {
            "repo_url": "https://github.com/runagent-dev/runagent.git",
            "path": "generated/custom",
            "author": "runagent-generator",
            "version": "1.0.0"
        },
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
        "input_fields": agent_info['input_fields'],
        "input_types": agent_info['input_types'],
        "input_descriptions": agent_info['input_descriptions'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def generate_custom_framework_files(agent_info: dict, session_dir: Path):
    """Generate custom framework files with proper input handling."""
    
    input_fields_str = json.dumps(agent_info['input_fields'])
    
    agent_code = f'''"""
{agent_info['agent_name']} - {agent_info['description']}
Generated by RunAgent Generator - Custom Framework
"""

def main(*input_args, **input_kwargs):
    """Main entry point for custom agent"""
    
    # Extract input from various sources
    input_parts = []
    for field in {input_fields_str}:
        if input_kwargs.get(field):
            input_parts.append(f"{{field}}: {{input_kwargs[field]}}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {{str(input_args[0])}}")
    
    if not input_parts:
        input_parts.append("Hello, how can I help you?")
    
    user_input = "\\n".join(input_parts)
    
    # Simple response for custom framework
    response = f"""
Hello! I'm {agent_info['agent_name']}.

{agent_info['description']}

You provided: {{user_input}}

My main functionality is: {agent_info['main_functionality']}

This is a custom framework implementation. You can modify this code to add your specific logic.
    """
    
    return response.strip()

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
    
    # Generate config
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
        "input_types": agent_info['input_types'],
        "input_descriptions": agent_info['input_descriptions'],
        "env_vars": {
            "OPENAI_API_KEY": "${OPENAI_API_KEY}"
        }
    }
    
    with open(session_dir / "runagent.config.json", "w") as f:
        json.dump(config, f, indent=2)

def start_runagent_server(session_dir: str, session_id: str):
    """Start runagent server and return connection info"""
    
    try:
        print(f"🚀 Starting RunAgent server for session: {session_id}")
        
        # Install dependencies
        print("📦 Installing agent dependencies...")
        try:
            result = subprocess.run(["pip", "install", "-r", "requirements.txt"], 
                                  cwd=session_dir, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
            else:
                print(f"⚠️ Dependency installation: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Dependency installation failed: {e}")
        
        # Set up environment
        env = os.environ.copy()
        env['RUNAGENT_DISABLE_DB'] = 'true'
        env['RUNAGENT_LOG_LEVEL'] = 'INFO'
        
        # Start RunAgent server
        cmd = ["runagent", "serve", "."]
        
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
        
        # Wait and extract info
        detected_port = None
        runagent_agent_id = None
        
        # Read output to get port and agent ID
        for i in range(50):
            try:
                line = process.stdout.readline()
                if line:
                    print(f"RunAgent: {line.strip()}")
                    
                    if "Allocated address:" in line and "127.0.0.1:" in line:
                        try:
                            port_part = line.split("127.0.0.1:")[-1].strip()
                            detected_port = int(port_part)
                            print(f"🔌 Detected Port: {detected_port}")
                        except:
                            pass
                    
                    if "New agent created with ID:" in line:
                        try:
                            runagent_agent_id = line.split("ID:")[-1].strip()
                            print(f"🆔 Detected RunAgent Agent ID: {runagent_agent_id}")
                        except:
                            pass
                    
                    if detected_port and runagent_agent_id:
                        break
                        
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Error reading line: {e}")
                break
        
        # Default values if not detected
        if not detected_port:
            detected_port = 8450
        if not runagent_agent_id:
            runagent_agent_id = str(uuid.uuid4())
        
        # Wait for server to initialize
        time.sleep(3)
        
        agent_url = f"http://localhost:8000/static/agent.html?agent={runagent_agent_id}"
        
        # Update session
        session = sessions.get(session_id, {})
        session["completion_time"] = time.time()
        session["runagent_port"] = detected_port
        session["agent_id"] = runagent_agent_id
        
        # Store running agent info
        running_agents[runagent_agent_id] = {
            "process": process,
            "agent_id": runagent_agent_id,
            "agent_url": agent_url,
            "port": detected_port,
            "runagent_url": f"http://localhost:{detected_port}",
            "session_id": session_id,
            "status": "active",
            "agent_info": session.get("agent_info", {})
        }
        
        print(f"🎉 RunAgent server started successfully!")
        return runagent_agent_id, agent_url, detected_port
        
    except Exception as e:
        print(f"❌ Error starting agent server: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def generate_agent_files(agent_info: dict, session_id: str):
    """Generate agent files based on framework and create test script"""
    
    try:
        # Create session directory
        session_dir = Path(f"generated_agents/{session_id}")
        session_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Creating agent files in: {session_dir}")
        print(f"Framework: {agent_info['framework']}")
        
        # Generate framework-specific files
        framework = agent_info['framework'].lower()
        
        if framework == 'langgraph':
            generate_langgraph_files(agent_info, session_dir)
        elif framework == 'letta':
            generate_letta_files(agent_info, session_dir)
        elif framework == 'agno':
            generate_agno_files(agent_info, session_dir)
        elif framework == 'llamaindex':
            generate_llamaindex_files(agent_info, session_dir)
        else:
            # Default to custom framework
            generate_custom_framework_files(agent_info, session_dir)
        
        # Generate agent test script
        print("Generating agent test script...")
        script_success = generate_agent_test_script(agent_info, session_dir)
        
        if not script_success:
            print("Warning: Test script generation had issues, but continuing...")
        
        # Generate .env file with basic setup
        env_content = """# Environment variables for the agent
OPENAI_API_KEY=${OPENAI_API_KEY}
RUNAGENT_LOG_LEVEL=INFO
RUNAGENT_DISABLE_DB=true
"""
        
        with open(session_dir / ".env", "w") as f:
            f.write(env_content)
        
        # Generate README
        readme_content = f"""# {agent_info['agent_name']}

{agent_info['description']}

## Framework
{agent_info['framework']}

## Usage

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run with RunAgent
```bash
runagent serve .
```

### Test the agent
```bash
python3 agent_test.py <agent_id> localhost <port> "your test message"
```

## Input Fields
{', '.join(agent_info['input_fields'])}

## Entrypoints
{', '.join(agent_info['entrypoint_tags'])}
"""
        
        with open(session_dir / "README.md", "w") as f:
            f.write(readme_content)
        
        print(f"Agent files generated successfully!")
        print(f"Files created:")
        for file_path in session_dir.glob("*"):
            print(f"   - {file_path.name}")
        
        return True
        
    except Exception as e:
        print(f"Error generating agent files: {e}")
        import traceback
        traceback.print_exc()
        return False

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for agent generation."""
    
    session_id = request.session_id or str(uuid.uuid4())
    message = request.message.strip()
    
    print(f"🔍 Received message: '{message}'")
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
**Expected Output:** {agent_info['expected_output_format']}

Let me create a workflow diagram for this agent..."""

            # Generate Mermaid diagram
            mermaid_diagram = generate_mermaid_diagram(agent_info)
            
            # Include SDK configuration in response
            sdk_config = {
                "inputFields": [
                    {
                        "name": field,
                        "type": agent_info['input_types'].get(field, "string"),
                        "description": agent_info['input_descriptions'].get(field, f"Enter {field}"),
                        "required": True,
                        "placeholder": f"Enter {field}..."
                    } for field in agent_info['input_fields']
                ],
                "entrypoints": [
                    {
                        "tag": tag,
                        "description": f"Main {'streaming' if 'stream' in tag else 'synchronous'} endpoint",
                        "streaming": "stream" in tag
                    } for tag in agent_info['entrypoint_tags']
                ],
                "exampleInputs": agent_info['example_inputs']
            }
            
            return ChatResponse(
                response=description,
                session_id=session_id,
                stage="planning",
                description=agent_info['description'],
                mermaid_diagram=mermaid_diagram,
                sdk_config=sdk_config
            )
        
        # Stage 2: Planning
        elif session["stage"] == "planning":
            if any(phrase in message.lower() for phrase in ["go for it", "generate", "create it", "build it", "make it", "proceed", "continue", "yes", "start"]):
                print(f"🚀 Starting agent generation for session {session_id}")
                
                # Generate agent files
                success = generate_agent_files(session["agent_info"], session_id)
                
                if not success:
                    raise Exception("Failed to generate agent files")
                
                session["files_generated"] = True
                session["stage"] = "starting"
                
                # Start RunAgent server in background
                session_dir_path = Path(f"generated_agents/{session_id}")
                
                def start_agent():
                    try:
                        agent_id, agent_url, port = start_runagent_server(str(session_dir_path), session_id)
                        
                        if agent_id and agent_url:
                            session["agent_id"] = agent_id
                            session["agent_url"] = agent_url
                            session["runagent_port"] = port
                            session["stage"] = "complete"
                            
                            running_agents[agent_id] = {
                                "agent_info": session["agent_info"],
                                "session_id": session_id,
                                "status": "active",
                                "port": port,
                                "runagent_url": f"http://localhost:{port}"
                            }
                        else:
                            session["stage"] = "error"
                            session["error"] = "Failed to start RunAgent server"
                    except Exception as e:
                        session["stage"] = "error"
                        session["error"] = str(e)
                
                threading.Thread(target=start_agent, daemon=True).start()
                
                return ChatResponse(
                    response=f"""✅ Agent files generated successfully! Now starting the RunAgent server...

🔄 Starting your **{session["agent_info"]["agent_name"]}** agent server...

This involves:
1. Installing {session["agent_info"]["framework"]} dependencies
2. Starting RunAgent server on available port
3. Initializing your agent with custom TypeScript SDK integration

⏳ Please wait 30-90 seconds, then **send any message** to check if it's ready.""",
                    session_id=session_id,
                    stage="starting"
                )
            else:
                # Handle modifications
                mermaid_diagram = generate_mermaid_diagram(session["agent_info"])
                return ChatResponse(
                    response="I can help you modify the agent. What would you like to change? Or say 'go for it' or 'generate' to proceed with the current design.",
                    session_id=session_id,
                    stage="planning",
                    description=session["agent_info"]["description"],
                    mermaid_diagram=mermaid_diagram
                )
        
        # Stage 3: Check agent status
        elif session["stage"] == "starting":
            if session.get("agent_id") and session.get("agent_url"):
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

Your {session["agent_info"]["framework"]} agent is running with:
- Dynamic input fields based on your requirements
- Custom TypeScript SDK integration
- Both synchronous and streaming endpoints

The agent interface will automatically configure inputs based on the generated SDK configuration!""",
                    session_id=session_id,
                    stage="complete",
                    agent_id=agent_id,
                    agent_url=agent_url
                )
            elif session.get("stage") == "error":
                error_msg = session.get("error", "Unknown error occurred")
                return ChatResponse(
                    response=f"❌ Error starting agent: {error_msg}\n\nPlease try again or check the server logs.",
                    session_id=session_id,
                    stage="error"
                )
            else:
                return ChatResponse(
                    response="""⏳ Still starting your agent server... 

The process includes:
- Installing dependencies
- Generating TypeScript SDK integration
- Initializing the RunAgent framework
- Starting the server and verifying connectivity

Please wait a bit longer and send another message to check status.""",
                    session_id=session_id,
                    stage="starting"
                )
        
        # Agent is complete
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

Your {session["agent_info"]["framework"]} agent is running with dynamic inputs and TypeScript SDK integration!""",
                    session_id=session_id,
                    stage="complete",
                    agent_id=agent_id,
                    agent_url=agent_url
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

@app.get("/agent/{agent_id}")
async def get_agent_info(agent_id: str):
    """Get comprehensive agent information"""
    try:
        print(f"Looking for agent ID: {agent_id}")
        
        # Find agent data
        agent_data = None
        session_id = None
        
        if agent_id in running_agents:
            agent_data = running_agents[agent_id]
            session_id = agent_data.get("session_id")
        else:
            # Check sessions
            for sid, session in sessions.items():
                if session.get("agent_id") == agent_id:
                    session_id = sid
                    agent_info = session.get("agent_info", {})
                    port = session.get("runagent_port", 8450)
                    agent_data = {
                        "agent_info": agent_info,
                        "port": port
                    }
                    break
        
        if not agent_data:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        agent_info = agent_data.get("agent_info", {})
        port = agent_data.get("port", 8450)
        
        # Check if test script exists
        script_available = False
        script_url = None
        if session_id:
            script_file = Path(f"generated_agents/{session_id}/agent_test.py")
            if script_file.exists():
                script_available = True
                script_url = f"http://localhost:8000/agent/{agent_id}/sdk"
        
        return {
            "agent_info": {
                "agent_name": agent_info.get("agent_name", "Unknown Agent"),
                "description": agent_info.get("description", "AI Agent"),
                "framework": agent_info.get("framework", "custom"),
                "input_fields": agent_info.get("input_fields", ["query"]),
                "input_types": agent_info.get("input_types", {"query": "string"}),
                "input_descriptions": agent_info.get("input_descriptions", {"query": "User input"}),
                "main_functionality": agent_info.get("main_functionality", "General assistance"),
                "expected_output_format": agent_info.get("expected_output_format", "String response"),
                "example_inputs": agent_info.get("example_inputs", [{"query": "Hello"}]),
                "entrypoint_tags": agent_info.get("entrypoint_tags", ["main", "main_stream"]),
                "port": port,
                "runagent_url": f"http://localhost:{port}",
                "runagent_agent_id": agent_id,
                "status": "ready",
                "script_available": script_available,
                "script_url": script_url,
                "session_id": session_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting agent info: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/agent/{agent_id}/sdk")
async def serve_agent_test_script(agent_id: str):
    """Serve the generated agent test script"""
    try:
        # Find the session directory
        session_id = None
        for sid, session in sessions.items():
            if session.get("agent_id") == agent_id:
                session_id = sid
                break
        
        if not session_id:
            raise HTTPException(status_code=404, detail="Agent session not found")
        
        test_file = Path(f"generated_agents/{session_id}/agent_test.py")
        if not test_file.exists():
            raise HTTPException(status_code=404, detail="Test script not found")
        
        # Read and return the test script
        with open(test_file, "r") as f:
            script_content = f.read()
        
        return Response(
            content=script_content,
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Content-Disposition": f"attachment; filename=agent_test_{agent_id}.py"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving test script: {str(e)}")


@app.get("/agent/{agent_id}/sdk-config")
async def get_agent_sdk_config(agent_id: str):
    """Get the generated SDK configuration for the agent"""
    try:
        # Find the session directory
        session_id = None
        for sid, session in sessions.items():
            if session.get("agent_id") == agent_id:
                session_id = sid
                break
        
        if not session_id:
            raise HTTPException(status_code=404, detail="Agent session not found")
        
        sdk_file = Path(f"generated_agents/{session_id}/sdk_test.js")
        if not sdk_file.exists():
            raise HTTPException(status_code=404, detail="SDK configuration not found")
        
        # Read and return the SDK file content
        with open(sdk_file, "r") as f:
            sdk_content = f.read()
        
        return {
            "agent_id": agent_id,
            "sdk_content": sdk_content,
            "file_path": str(sdk_file)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading SDK config: {str(e)}")

@app.get("/debug/test-agent/{agent_id}")
async def debug_test_agent(agent_id: str, test_input: str = "Hello, how can you help me?"):
    """Debug endpoint to test agent functionality directly"""
    try:
        import requests
        
        # Find agent info
        agent_data = None
        if agent_id in running_agents:
            agent_data = running_agents[agent_id]
        else:
            # Check sessions
            for session_id, session in sessions.items():
                if session.get("agent_id") == agent_id:
                    port = session.get("runagent_port", 8450)
                    agent_info = session.get("agent_info", {})
                    agent_data = {
                        "port": port,
                        "agent_info": agent_info
                    }
                    break
        
        if not agent_data:
            return {"error": f"Agent {agent_id} not found"}
        
        port = agent_data.get("port", 8450)
        agent_info = agent_data.get("agent_info", {})
        base_url = f"http://localhost:{port}"
        
        # Get first input field name
        input_fields = agent_info.get("input_fields", ["query"])
        first_field = input_fields[0] if input_fields else "query"
        
        test_data = {first_field: test_input}
        
        # Test different endpoints
        endpoints_to_test = [
            "/agents/main/run",
            "/agents/main/invoke", 
            "/run",
            "/invoke"
        ]
        
        results = {}
        
        for endpoint in endpoints_to_test:
            try:
                response = requests.post(
                    f"{base_url}{endpoint}",
                    json=test_data,
                    timeout=10
                )
                
                results[endpoint] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "content": response.text[:500] if response.text else "",
                    "headers": dict(response.headers)
                }
                
            except Exception as e:
                results[endpoint] = {
                    "status_code": "error",
                    "success": False,
                    "error": str(e)
                }
        
        return {
            "agent_id": agent_id,
            "port": port,
            "base_url": base_url,
            "test_input": test_data,
            "results": results,
            "agent_info": {
                "name": agent_info.get("agent_name", "Unknown"),
                "framework": agent_info.get("framework", "unknown"),
                "input_fields": input_fields
            }
        }
        
    except Exception as e:
        return {"error": f"Debug test failed: {str(e)}"}

from fastapi.responses import StreamingResponse
import asyncio

@app.get("/agent/{agent_id}/run-test-stream")
async def run_streaming_test_live(
    agent_id: str, 
    test_message: str = "Hello, streaming test",
    input_data: str = None,
    entrypoint_tag: str = None
):
    """Live streaming test that sends output as it's generated"""
    try:
        # Find the session directory
        session_id = None
        for sid, session in sessions.items():
            if session.get("agent_id") == agent_id:
                session_id = sid
                break
        
        if not session_id:
            raise HTTPException(status_code=404, detail="Agent session not found")
        
        session_dir = Path(f"generated_agents/{session_id}")
        session = sessions[session_id]
        agent_info = session.get("agent_info", {})
        port = session.get("runagent_port", 8450)
        
        # Parse input data if provided
        dynamic_inputs = {}
        if input_data:
            try:
                dynamic_inputs = json.loads(input_data)
            except json.JSONDecodeError:
                pass
        
        # Create the enhanced test script (same as before)
        temp_script_content = f'''import sys
import json
import time
import os

# Use line buffering for real-time output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, "{str(session_dir)}")

def enhanced_streaming_test():
    agent_id = "{agent_id}"
    host = "localhost"
    port = {port}
    test_message = "{test_message}"
    
    print(f"🧪 Starting Streaming Test")
    print(f"🔌 Connection: {{host}}:{{port}}")
    print(f"📝 Test Message: {{test_message}}")
    print("=" * 50)
    
    # Dynamic inputs
    dynamic_inputs = {json.dumps(dynamic_inputs)}
    
    from runagent import RunAgentClient
    
    # Find streaming entrypoint
    all_entrypoints = {agent_info['entrypoint_tags']}
    streaming_tags = [tag for tag in all_entrypoints if "stream" in tag.lower()]
    
    if not streaming_tags:
        streaming_tags = all_entrypoints
    
    target_tag = "{entrypoint_tag}" if "{entrypoint_tag}" else streaming_tags[0] if streaming_tags else "main_stream"
    
    print(f"🎯 Using entrypoint: {{target_tag}}")
    print("-" * 40)
    
    # Prepare input data
    if dynamic_inputs:
        input_data = dynamic_inputs.copy()
    else:
        primary_field = "{agent_info['input_fields'][0] if agent_info['input_fields'] else 'query'}"
        input_data = {{primary_field: test_message}}
    
    try:
        ra = RunAgentClient(
            agent_id=agent_id,
            entrypoint_tag=target_tag,
            local=True
        )
        
        print(f"✅ Client created successfully")
        print(f"📡 Starting stream...")
        print("-" * 40)
        
        chunk_count = 0
        for chunk in ra.run(**input_data):
            chunk_count += 1
            
            # Handle different chunk types
            if isinstance(chunk, dict):
                content = chunk.get('content', '')
                if content:
                    print(content, end="", flush=True)
                else:
                    print(str(chunk), flush=True)
            else:
                print(chunk, end="", flush=True)
            
            if chunk_count > 200:  # Prevent infinite loops
                print("\\n... [truncated after 200 chunks]")
                break
        
        print(f"\\n-" * 40)
        print(f"🎉 Stream completed with {{chunk_count}} chunks")
        
    except Exception as e:
        print(f"❌ Streaming error: {{str(e)}}")

if __name__ == "__main__":
    enhanced_streaming_test()
'''
        
        # Write the streaming test script
        temp_script = session_dir / "streaming_test.py"
        with open(temp_script, "w") as f:
            f.write(temp_script_content)
        
        async def generate_stream():
            """Generator function for streaming output"""
            try:
                # Prepare environment
                env = os.environ.copy()
                env['PYTHONPATH'] = str(Path.cwd())
                env['PYTHONUNBUFFERED'] = '1'
                
                # Start the process
                process = subprocess.Popen(
                    ["python3", "streaming_test.py"],
                    cwd=session_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env
                )
                
                # Read output line by line as it's generated
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        # Send as Server-Sent Event format
                        yield f"data: {json.dumps({'type': 'output', 'content': output.rstrip()})}\n\n"
                        await asyncio.sleep(0.01)  # Small delay for better streaming effect
                
                # Send completion event
                return_code = process.poll()
                yield f"data: {json.dumps({'type': 'complete', 'return_code': return_code})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            finally:
                # Clean up temp script
                if temp_script.exists():
                    temp_script.unlink()
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming test failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_sessions": len(sessions)}

@app.get("/debug/clear-sessions")
async def clear_sessions():
    """Clear all sessions and running agents for debugging."""
    global sessions, running_agents
    
    # Stop any running processes
    for agent_id, agent_data in running_agents.items():
        if "process" in agent_data and agent_data["process"]:
            try:
                agent_data["process"].terminate()
                print(f"🛑 Terminated process for agent {agent_id}")
            except:
                pass
    
    sessions.clear()
    running_agents.clear()
    
    return {"message": "All sessions and agents cleared", "status": "success"}

@app.get("/agent/{agent_id}/run-test")
async def run_python_sdk_test(
    agent_id: str, 
    test_message: str = "Hello, how can you help me?",
    input_data: str = None,
    streaming: bool = False,
    entrypoint_tag: str = None
):
    """Run the Python SDK test with dynamic input data and streaming support"""
    try:
        # Find the session directory
        session_id = None
        for sid, session in sessions.items():
            if session.get("agent_id") == agent_id:
                session_id = sid
                break
        
        if not session_id:
            raise HTTPException(status_code=404, detail="Agent session not found")
        
        session_dir = Path(f"generated_agents/{session_id}")
        python_file = session_dir / "agent_test.py"
        
        if not python_file.exists():
            raise HTTPException(status_code=404, detail="Python SDK file not found")
        
        # Get agent info
        session = sessions[session_id]
        agent_info = session.get("agent_info", {})
        port = session.get("runagent_port", 8450)
        
        # Parse input data if provided
        dynamic_inputs = {}
        if input_data:
            try:
                dynamic_inputs = json.loads(input_data)
                print(f"📋 Using dynamic inputs: {dynamic_inputs}")
            except json.JSONDecodeError:
                print(f"⚠️ Failed to parse input_data, using test_message only")
        
        # Prepare environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())
        
        # Create a temporary script that handles dynamic inputs and proper content extraction
        temp_script_content = f'''import sys
import json
import os
sys.path.insert(0, os.path.dirname(__file__))

def enhanced_main():
    if len(sys.argv) < 5:
        print("Usage: python3 enhanced_test.py <agent_id> <host> <port> <test_message> [streaming] [entrypoint]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    host = sys.argv[2] 
    port = int(sys.argv[3])
    test_message = sys.argv[4]
    streaming_mode = sys.argv[5] if len(sys.argv) > 5 else "false"
    target_entrypoint = sys.argv[6] if len(sys.argv) > 6 else None
    
    print(f"🧪 Enhanced Testing Agent: {{agent_id}}")
    print(f"🔌 Connection: {{host}}:{{port}}")
    print(f"📝 Test Message: {{test_message}}")
    print(f"🌊 Streaming Mode: {{streaming_mode}}")
    if target_entrypoint:
        print(f"🎯 Target Entrypoint: {{target_entrypoint}}")
    
    # Use dynamic inputs if available
    dynamic_inputs = {json.dumps(dynamic_inputs)}
    
    from runagent import RunAgentClient
    import time
    
    # Determine entrypoints to test
    all_entrypoints = {agent_info['entrypoint_tags']}
    
    if target_entrypoint:
        entrypoints_to_test = [target_entrypoint]
    elif streaming_mode.lower() == "true":
        entrypoints_to_test = [tag for tag in all_entrypoints if "stream" in tag.lower()]
        if not entrypoints_to_test:
            entrypoints_to_test = all_entrypoints
    else:
        # For non-streaming, prefer non-stream entrypoints
        entrypoints_to_test = [tag for tag in all_entrypoints if "stream" not in tag.lower()]
        if not entrypoints_to_test:
            entrypoints_to_test = all_entrypoints
    
    print(f"🎯 Testing entrypoints: {{entrypoints_to_test}}")
    print("=" * 60)
    
    # Prepare input data
    if dynamic_inputs:
        input_data = dynamic_inputs.copy()
        print(f"📋 Using dynamic inputs: {{json.dumps(input_data, indent=2)}}")
    else:
        # Fallback to test message mapping
        primary_field = "{agent_info['input_fields'][0] if agent_info['input_fields'] else 'query'}"
        input_data = {{primary_field: test_message}}
        print(f"📋 Using fallback input: {{json.dumps(input_data, indent=2)}}")
    
    # Test each entrypoint
    for i, tag in enumerate(entrypoints_to_test, 1):
        try:
            print(f"\\n🎯 Attempt {{i}}/{{len(entrypoints_to_test)}}: Testing '{{tag}}'")
            start_time = time.time()
            
            ra = RunAgentClient(
                agent_id=agent_id,
                entrypoint_tag=tag,
                local=True
            )
            
            print(f"✅ RunAgentClient created successfully")
            
            if "stream" in tag.lower() or streaming_mode.lower() == "true":
                print("📡 Testing streaming mode:")
                print("-" * 40)
                chunk_count = 0
                accumulated_content = ""
                
                for chunk in ra.run(**input_data):
                    chunk_count += 1
                    
                    # Extract content from chunk if it's a dict
                    if isinstance(chunk, dict):
                        content = chunk.get('content', '')
                        if content:
                            print(content, end="", flush=True)
                            accumulated_content += content
                    else:
                        print(chunk, end="", flush=True)
                        accumulated_content += str(chunk)
                    
                    if chunk_count > 200:  # Prevent infinite loops
                        print("\\n... [truncated after 200 chunks]")
                        break
                
                print(f"\\n-" * 40)
                print(f"📊 Received {{chunk_count}} chunks")
                print(f"📏 Total content length: {{len(accumulated_content)}} characters")
                
            else:
                print("🔄 Testing synchronous mode:")
                result = ra.run(**input_data)
                
                print(f"📤 Result Type: {{type(result)}}")
                
                # Handle different result types
                if isinstance(result, dict):
                    if 'content' in result:
                        content = result['content']
                        if hasattr(content, '__iter__') and not isinstance(content, str):
                            # If content is a generator or iterator, consume it
                            try:
                                if hasattr(content, '__next__'):
                                    print("🔄 Consuming generator/iterator result:")
                                    consumed_content = ""
                                    chunk_count = 0
                                    for chunk in content:
                                        if isinstance(chunk, dict) and 'content' in chunk:
                                            consumed_content += chunk['content']
                                        else:
                                            consumed_content += str(chunk)
                                        chunk_count += 1
                                        if chunk_count > 100:
                                            consumed_content += "... [truncated]"
                                            break
                                    print(f"📤 Consumed Content:\\n{{consumed_content}}")
                                else:
                                    print(f"📤 Content: {{content}}")
                            except Exception as e:
                                print(f"⚠️ Error consuming iterator: {{e}}")
                                print(f"📤 Raw Content: {{content}}")
                        else:
                            print(f"📤 Content:\\n{{content}}")
                    else:
                        print(f"📤 Full Result:")
                        result_str = json.dumps(result, indent=2, default=str)
                        print(result_str[:2000] + "..." if len(result_str) > 2000 else result_str)
                else:
                    result_str = str(result)
                    print(f"📤 Result Content:")
                    print(result_str[:2000] + "..." if len(result_str) > 2000 else result_str)
            
            elapsed = time.time() - start_time
            print(f"\\n⏱️  Execution Time: {{elapsed:.2f}} seconds")
            print(f"🎉 SUCCESS! Agent responded via entrypoint '{{tag}}'")
            sys.exit(0)
            
        except Exception as e:
            print(f"❌ Failed with entrypoint '{{tag}}': {{str(e)}}")
            if i < len(entrypoints_to_test):
                print("🔄 Trying next entrypoint...")
            continue
    
    print(f"\\n💥 All {{len(entrypoints_to_test)}} entrypoints failed!")
    sys.exit(1)

if __name__ == "__main__":
    enhanced_main()
'''
        
        # Write the enhanced test script
        temp_script = session_dir / "enhanced_test.py"
        with open(temp_script, "w") as f:
            f.write(temp_script_content)
        
        # Prepare command arguments
        cmd_args = [
            "python3", "enhanced_test.py", 
            agent_id, "localhost", str(port), test_message
        ]
        
        if streaming:
            cmd_args.append("true")
            if entrypoint_tag:
                cmd_args.append(entrypoint_tag)
        
        print(f"🚀 Running command: {' '.join(cmd_args)}")
        
        # Run the enhanced test
        test_result = subprocess.run(
            cmd_args,
            cwd=session_dir,
            capture_output=True,
            text=True,
            timeout=120,  # Increased timeout for streaming
            env=env
        )
        
        # Clean up temp script
        if temp_script.exists():
            temp_script.unlink()
        
        success = test_result.returncode == 0
        
        return {
            "success": success,
            "test_stdout": test_result.stdout,
            "test_stderr": test_result.stderr,
            "agent_info": {
                "name": agent_info.get("agent_name", "Unknown"),
                "framework": agent_info.get("framework", "unknown"),
                "port": port,
                "input_fields": agent_info.get("input_fields", []),
                "entrypoint_tags": agent_info.get("entrypoint_tags", [])
            },
            "sdk_type": "python",
            "streaming_mode": streaming,
            "dynamic_inputs_used": bool(dynamic_inputs),
            "inputs_received": dynamic_inputs if dynamic_inputs else {"test_message": test_message}
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Test timeout (120s exceeded)",
            "sdk_type": "python",
            "streaming_mode": streaming
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Test failed: {str(e)}",
            "sdk_type": "python",
            "streaming_mode": streaming
        }

if __name__ == "__main__":
    import uvicorn
    
    # Create directories
    os.makedirs("generated_agents", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)