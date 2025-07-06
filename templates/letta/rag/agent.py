import os
from typing import Any, Dict

from dotenv import load_dotenv
from letta_client import CreateBlock, Letta
from rag_tool import rag_tool

# Load environment variables
load_dotenv()


# def _extract_message_from_input(*input_args, **input_kwargs) -> str:
#     if input_kwargs.get("message"):
#         return str(input_kwargs["message"])
    
#     return "Failed to extract input"


def _register_tools(client: Letta) -> Dict[str, str]:
    """Register tools with Letta client"""
    tool_fns = [
        rag_tool
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


def letta_run(message:str):
    """Simple function that runs Letta agent with RAG and keyword tools"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Register tools
        print("🔧 Registering tools...")
        tool_map = _register_tools(client)
        
        # Create memory blocks with astrology context
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are talking to a user interested in astrology and cosmic knowledge through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="You are an expert astrology assistant with access to a comprehensive astrology knowledge base and research tools.",
            ),
        ]

        # Create agent with tools and astrology context
        agent = client.agents.create(
            name=f"runagent-astro-letta-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="You are an expert astrology assistant with access to powerful research tools. You have:\n\n1. **RAG tool (rag_tool)** - Use this to search through a comprehensive astrology knowledge base. Use mode='mix' for best results.When users ask about astrology topics, use the rag_tool to search for relevant information.",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            tool_ids=list(tool_map.values()),  # Add the registered tools
            include_base_tools=True
        )

        print(f"✅ Astrology Letta agent created with ID: {agent.id}")
        print(f"🛠️ Agent has {len(tool_map)} custom tools available (RAG + Keywords)")
        
        # Extract message from input
        # message = _extract_message_from_input(*input_args, **input_kwargs)
        
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
    """Simple function that streams from Letta agent with RAG and keyword tools"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Register tools
        print("🔧 Registering tools for streaming...")
        tool_map = _register_tools(client)
        
        # Create memory blocks with astrology context
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are talking to a user interested in astrology and cosmic knowledge through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="You are an expert astrology assistant with access to a comprehensive astrology knowledge base and research tools. You can extract keywords from text and search through astrological texts to provide detailed, accurate information about astrology, zodiac signs, planetary influences, and cosmic phenomena. Be knowledgeable, insightful, and helpful.",
            ),
        ]

        # Create agent with tools and astrology context
        agent = client.agents.create(
            name=f"runagent-astro-letta-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="You are an expert astrology assistant with access to powerful research tools. You have:\n\n1. **RAG tool (rag_tool)** - Use this to search through a comprehensive astrology knowledge base. Use mode='mix' for best results.When users ask about astrology topics, use the rag_tool to search for relevant information.",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            tool_ids=list(tool_map.values()),  # Add the registered tools
            include_base_tools=True
        )

        print(f"✅ Astrology streaming agent created with ID: {agent.id}")
        print(f"🛠️ Streaming agent has {len(tool_map)} custom tools available (RAG + Keywords)")
        
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
            
    except Exception as e:
        yield f"Letta streaming error: {str(e)}"