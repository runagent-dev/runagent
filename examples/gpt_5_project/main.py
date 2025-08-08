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

def generate_typescript_sdk_test(agent_info: dict, session_dir: Path):
    """Generate TypeScript SDK test file with GPT-5"""
    
    prompt = f"""
    Generate a TypeScript/JavaScript SDK test file for this AI agent using the provided template as reference:
    
    Agent Name: {agent_info['agent_name']}
    Framework: {agent_info['framework']}
    Description: {agent_info['description']}
    Input Fields: {agent_info['input_fields']}
    Input Types: {agent_info['input_types']}
    Input Descriptions: {agent_info['input_descriptions']}
    Expected Output: {agent_info['expected_output_format']}
    Example Inputs: {agent_info['example_inputs']}
    Entrypoint Tags: {agent_info['entrypoint_tags']}
    
    Create a complete TypeScript/JavaScript file that:
    1. Exports a function `getAgentConfig()` that returns configuration for the dynamic UI
    2. Exports a function `testAgent(agentId, host, port, inputValues, entrypointTag)` that tests the agent
    3. Exports a function `testAgentStream(agentId, host, port, inputValues, entrypointTag)` for streaming
    4. Includes proper error handling and endpoint discovery
    5. Uses HTTP fetch fallback since RunAgent TypeScript SDK may not be available
    6. Provides detailed logging and debugging information
    7. Validates inputs and formats outputs appropriately
    
    The getAgentConfig() should return an object with:
    - agentName: string
    - description: string  
    - framework: string
    - inputFields: array of field configurations with name, type, description, required, placeholder
    - entrypoints: array of entrypoint configurations with tag, description, streaming
    - exampleInputs: array of example input objects
    
    Make the input fields specific to this agent type. For example:
    - Weather agent: location, units, forecast_days
    - Math solver: expression, show_steps, precision
    - Research agent: topic, depth, max_sources, include_citations
    - Content writer: topic, style, tone, word_count, format
    
    Use appropriate input types:
    - "string" for text inputs
    - "number" for numeric inputs
    - "boolean" for checkboxes  
    - "textarea" for longer text inputs
    
    Make the testAgent function robust with multiple endpoint fallbacks and detailed error reporting.
    Include the window attachment code at the end for browser compatibility.
    
    Focus on making this agent-specific and functional. Return only the JavaScript code.
    """
    
    try:
        response = openai_client.responses.create(
            model="gpt-5-mini",
            input=prompt,
            reasoning={"effort": "minimal"}
        )
        
        sdk_code = response.output[1].content[0].text
        
        # Clean up the code
        sdk_code = sdk_code.replace('```typescript', '').replace('```javascript', '').replace('```', '').strip()
        
        # Ensure it includes browser compatibility
        if 'window.testAgent' not in sdk_code:
            sdk_code += '''

// Browser compatibility - attach functions to window
if (typeof window !== 'undefined') {
    window.testAgent = testAgent;
    window.testAgentStream = testAgentStream; 
    window.getAgentConfig = getAgentConfig;
    console.log('✅ SDK functions attached to window');
}'''
        
        # Write to file
        with open(session_dir / "sdk_test.js", "w") as f:
            f.write(sdk_code)
        
        print(f"✅ Generated TypeScript SDK test file for {agent_info['agent_name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating TypeScript SDK test: {e}")
        
        # Enhanced fallback SDK code
        fallback_code = f'''// Generated SDK test for {agent_info['agent_name']}
// Framework: {agent_info['framework']}

export function getAgentConfig() {{
    return {{
        agentName: "{agent_info['agent_name']}",
        description: "{agent_info['description']}",
        framework: "{agent_info['framework']}",
        inputFields: [
            {',\\n            '.join([
                '{{\\n                name: "{}",\\n                type: "{}",\\n                description: "{}",\\n                required: true,\\n                placeholder: "{}"\\n            }}'.format(
                    field,
                    agent_info['input_types'].get(field, "string"),
                    agent_info['input_descriptions'].get(field, f"Enter {field}"),
                    f"Enter {field}..."
                ) for field in agent_info['input_fields']
            ])}
        ],
        entrypoints: [
            {',\\n            '.join([
                '{{\\n                tag: "{}",\\n                description: "{}",\\n                streaming: {}\\n            }}'.format(
                    tag,
                    f"{'Streaming' if 'stream' in tag else 'Synchronous'} endpoint for {agent_info['framework']}",
                    'true' if 'stream' in tag else 'false'
                ) for tag in agent_info['entrypoint_tags']
            ])}
        ],
        exampleInputs: {json.dumps(agent_info['example_inputs'], indent=12)}
    }};
}}

export async function testAgent(agentId, host, port, inputValues, entrypointTag = "main") {{
    try {{
        console.log('🧪 Testing {agent_info['agent_name']} agent...');
        console.log('📝 Input values:', inputValues);
        console.log('🎯 Using entrypoint:', entrypointTag);
        
        const baseUrl = `http://${{host}}:${{port}}`;
        const endpointsToTry = [
            `/agents/${{entrypointTag}}/run`,
            `/agents/${{entrypointTag}}/invoke`,
            `/run`,
            `/invoke`,
            `/${{entrypointTag}}`
        ];
        
        let lastError = null;
        
        for (const endpoint of endpointsToTry) {{
            try {{
                const url = `${{baseUrl}}${{endpoint}}`;
                console.log(`🔗 Trying: ${{endpoint}}`);
                
                const response = await fetch(url, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(inputValues)
                }});
                
                if (response.ok) {{
                    const result = await response.text();
                    console.log('✅ SUCCESS with:', endpoint);
                    
                    return {{
                        success: true,
                        result: result,
                        endpoint: endpoint,
                        method: 'http_direct',
                        statusCode: response.status,
                        inputValues: inputValues
                    }};
                }} else {{
                    const errorText = await response.text().catch(() => 'No error details');
                    lastError = `HTTP ${{response.status}}: ${{errorText}}`;
                    console.log(`❌ ${{endpoint}} failed: ${{response.status}}`);
                }}
                
            }} catch (error) {{
                lastError = error.message;
                console.log(`❌ ${{endpoint}} error:`, error.message);
                continue;
            }}
        }}
        
        throw new Error(`All endpoints failed. Last error: ${{lastError}}`);
        
    }} catch (error) {{
        console.error('❌ Agent test failed:', error);
        return {{
            success: false,
            error: error.message,
            method: 'failed',
            inputValues: inputValues
        }};
    }}
}}

export async function testAgentStream(agentId, host, port, inputValues, entrypointTag = "main_stream") {{
    try {{
        console.log('🌊 Testing {agent_info['agent_name']} agent streaming...');
        
        const baseUrl = `http://${{host}}:${{port}}`;
        const endpointsToTry = [
            `/agents/${{entrypointTag}}/stream`,
            `/agents/${{entrypointTag}}/run`,
            `/stream`,
            `/${{entrypointTag}}`
        ];
        
        for (const endpoint of endpointsToTry) {{
            try {{
                const url = `${{baseUrl}}${{endpoint}}`;
                console.log(`🔗 Trying streaming: ${{endpoint}}`);
                
                const response = await fetch(url, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(inputValues)
                }});
                
                if (response.ok) {{
                    let result = '';
                    
                    if (response.body) {{
                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();
                        
                        while (true) {{
                            const {{ done, value }} = await reader.read();
                            if (done) break;
                            result += decoder.decode(value);
                        }}
                    }} else {{
                        result = await response.text();
                    }}
                    
                    return {{
                        success: true,
                        result: result,
                        endpoint: endpoint,
                        method: 'http_stream',
                        streaming: true,
                        inputValues: inputValues
                    }};
                }}
                
            }} catch (error) {{
                console.log(`❌ ${{endpoint}} streaming error:`, error.message);
                continue;
            }}
        }}
        
        throw new Error('All streaming endpoints failed');
        
    }} catch (error) {{
        console.error('❌ Streaming test failed:', error);
        return {{
            success: false,
            error: error.message,
            method: 'failed',
            streaming: false,
            inputValues: inputValues
        }};
    }}
}}

// Browser compatibility
if (typeof window !== 'undefined') {{
    window.testAgent = testAgent;
    window.testAgentStream = testAgentStream;
    window.getAgentConfig = getAgentConfig;
    console.log('✅ {agent_info['agent_name']} SDK functions loaded');
}}
'''
        
        with open(session_dir / "sdk_test.js", "w") as f:
            f.write(fallback_code)
        
        print(f"✅ Generated fallback SDK for {agent_info['agent_name']}")
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

def generate_agent_files(agent_info: dict, session_id: str) -> bool:
    """Generate agent files based on template and user requirements."""
    
    framework = agent_info['framework']
    
    # Create session directory
    session_dir = Path(f"generated_agents/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Create .env file
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
            generate_custom_framework_files(agent_info, session_dir)
        
        # Generate TypeScript SDK test file
        generate_typescript_sdk_test(agent_info, session_dir)
        
        # Validate config file
        config_file = session_dir / "runagent.config.json"
        if not config_file.exists():
            raise Exception("Config file was not created")
        
        with open(config_file, "r") as f:
            config = json.load(f)
        
        required_fields = ["agent_name", "description", "framework", "template_source", "agent_architecture"]
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise Exception(f"Config missing required fields: {missing_fields}")
        
        print(f"✅ Successfully generated and validated {framework} agent")
        return True
        
    except Exception as e:
        print(f"❌ Error generating {framework} files: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    """Get comprehensive agent information including SDK configuration"""
    try:
        print(f"🔍 Looking for agent ID: {agent_id}")
        
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
        
        # Check if SDK file exists
        sdk_available = False
        sdk_url = None
        if session_id:
            sdk_file = Path(f"generated_agents/{session_id}/sdk_test.js")
            if sdk_file.exists():
                sdk_available = True
                sdk_url = f"http://localhost:8000/agent/{agent_id}/sdk"
        
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
                "sdk_available": sdk_available,
                "sdk_url": sdk_url,
                "session_id": session_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting agent info: {e}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/agent/{agent_id}/sdk")
async def serve_agent_sdk(agent_id: str):
    """Serve the generated SDK JavaScript file for dynamic loading"""
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
            raise HTTPException(status_code=404, detail="SDK file not found")
        
        # Read and return the SDK file with proper content type
        with open(sdk_file, "r") as f:
            sdk_content = f.read()
        
        return Response(
            content=sdk_content,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving SDK: {str(e)}")

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

@app.get("/debug/agent-files/{agent_id}")
async def debug_agent_files(agent_id: str):
    """Debug endpoint to show generated agent files"""
    try:
        # Find the session directory
        session_id = None
        for sid, session in sessions.items():
            if session.get("agent_id") == agent_id:
                session_id = sid
                break
        
        if not session_id:
            return {"error": "Agent session not found"}
        
        session_dir = Path(f"generated_agents/{session_id}")
        if not session_dir.exists():
            return {"error": "Session directory not found"}
        
        files_info = {}
        
        # Check common files
        common_files = [
            "runagent.config.json",
            "agent.py", 
            "requirements.txt",
            "sdk_test.js",
            ".env"
        ]
        
        for filename in common_files:
            file_path = session_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, "r") as f:
                        content = f.read()
                    files_info[filename] = {
                        "exists": True,
                        "size": len(content),
                        "content_preview": content[:500] + "..." if len(content) > 500 else content
                    }
                except Exception as e:
                    files_info[filename] = {
                        "exists": True,
                        "error": f"Could not read: {str(e)}"
                    }
            else:
                files_info[filename] = {"exists": False}
        
        return {
            "agent_id": agent_id,
            "session_id": session_id,
            "session_dir": str(session_dir),
            "files": files_info
        }
        
    except Exception as e:
        return {"error": f"Debug failed: {str(e)}"}

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

if __name__ == "__main__":
    import uvicorn
    
    # Create directories
    os.makedirs("generated_agents", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
