import os
from typing import Any, Dict

from dotenv import load_dotenv
from letta_client import CreateBlock, Letta
from keyword_tool import extract_keywords

# Load environment variables
load_dotenv()


def _extract_message_from_input(*input_args, **input_kwargs) -> str:
    """Extract message text from various input formats"""
    # # Try messages list format
    # if input_kwargs.get("messages"):
    #     messages = input_kwargs["messages"]
    #     if isinstance(messages, list) and messages:
    #         last_message = messages[-1]
    #         if isinstance(last_message, dict) and "content" in last_message:
    #             return last_message["content"]
    
    # Try direct message parameter
    if input_kwargs.get("message"):
        return str(input_kwargs["message"])
    
    # # Try first positional argument as string
    # if input_args and isinstance(input_args[0], str):
    #     return input_args[0]
    
    # # Try first positional argument as dict with messages
    # if input_args and isinstance(input_args[0], dict):
    #     data = input_args[0]
    #     if "messages" in data and isinstance(data["messages"], list) and data["messages"]:
    #         last_message = data["messages"][-1]
    #         if isinstance(last_message, dict) and "content" in last_message:
    #             return last_message["content"]
    
    # Fallback
    return "Failed to extract input"


def _register_tools(client: Letta) -> Dict[str, str]:
    """Register tools with Letta client"""
    tool_fns = [
        extract_keywords,
    ]

    # Register tools using the client.tools.upsert_from_function method
    tool_map: Dict[str, str] = {}
    registration_success = True

    for fn in tool_fns:
        try:
            print(f"  📝 Registering {fn.__name__}...")
            tool = client.tools.upsert_from_function(func=fn)
            tool_map[tool.name] = tool.id
            print(f"  ✅ Successfully registered: {tool.name} -> {tool.id}")
        except Exception as e:
            print(f"  ❌ Failed to register tool {fn.__name__}: {e}")
            registration_success = False

    if not registration_success:
        print("❌ Tool registration failed. Check the errors above.")
        
    return tool_map


def letta_run(*input_args, **input_kwargs):
    """Simple function that runs Letta agent with tools"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Register tools
        print("🔧 Registering tools...")
        tool_map = _register_tools(client)
        
        # Create memory blocks
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are talking to a user through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="You are a helpful AI assistant with access to keyword extraction tools. Be friendly and concise.",
            ),
        ]

        # Create agent with tools
        agent = client.agents.create(
            name=f"runagent-letta-tools-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="You are a helpful AI assistant with access to keyword extraction tools. When users ask about extracting keywords from text, must use the **extract_keywords tool**. Respond naturally and helpfully.",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            tool_ids=list(tool_map.values()),  # Add the registered tools
            include_base_tools=True
        )

        print(f"✅ Letta agent created with ID: {agent.id}")
        print(f"🛠️ Agent has {len(tool_map)} custom tools available")
        
        # Extract message from input
        message = _extract_message_from_input(*input_args, **input_kwargs)
        
        # Send message to Letta agent
        response = client.agents.messages.create(
            agent_id=agent.id,
            messages=[{
                "role": "user",
                "content": message
            }]
        )
        

            
        return response
        
    except Exception as e:
        return f"Letta execution error: {str(e)}"


def letta_run_stream(*input_args, **input_kwargs):
    """Simple function that streams from Letta agent with tools"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Register tools
        print("🔧 Registering tools for streaming...")
        tool_map = _register_tools(client)
        
        # Create memory blocks
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are talking to a user through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="You are a helpful AI assistant with access to keyword extraction tools. Be friendly and concise.",
            ),
        ]

        # Create agent with tools
        agent = client.agents.create(
            name=f"runagent-letta-stream-tools-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="You are a helpful AI assistant with access to keyword extraction tools. When users ask about extracting keywords from text, use the extract_keywords tool. Respond naturally and helpfully.",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            tool_ids=list(tool_map.values()),  # Add the registered tools
            include_base_tools=True
        )

        print(f"✅ Letta streaming agent created with ID: {agent.id}")
        print(f"🛠️ Streaming agent has {len(tool_map)} custom tools available")
        
        # Extract message from input
        message = _extract_message_from_input(*input_args, **input_kwargs)
        
        # Create streaming response
        stream = client.agents.messages.create_stream(
            agent_id=agent.id,
            messages=[{
                "role": "user",
                "content": message
            }],
            stream_tokens=True,
        )
        
        # Yield chunks
        for chunk in stream:
            yield chunk
        
        # Clean up agent after use
        try:
            client.agents.delete(agent.id)
            print(f"🗑️ Cleaned up streaming agent: {agent.id}")
        except:
            pass  # Ignore cleanup errors
            
    except Exception as e:
        yield f"Letta streaming error: {str(e)}"