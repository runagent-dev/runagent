import os
from typing import Any

from dotenv import load_dotenv
from letta_client import CreateBlock, Letta

# Load environment variables
load_dotenv()


def _extract_message_from_input(*input_args, **input_kwargs) -> str:
    """Extract message text from various input formats"""
    # Try messages list format
    if input_kwargs.get("messages"):
        messages = input_kwargs["messages"]
        if isinstance(messages, list) and messages:
            last_message = messages[-1]
            if isinstance(last_message, dict) and "content" in last_message:
                return last_message["content"]
    
    # Try direct message parameter
    if input_kwargs.get("message"):
        return str(input_kwargs["message"])
    
    # Try first positional argument as string
    if input_args and isinstance(input_args[0], str):
        return input_args[0]
    
    # Try first positional argument as dict with messages
    if input_args and isinstance(input_args[0], dict):
        data = input_args[0]
        if "messages" in data and isinstance(data["messages"], list) and data["messages"]:
            last_message = data["messages"][-1]
            if isinstance(last_message, dict) and "content" in last_message:
                return last_message["content"]
    
    # Fallback
    return "Failed to extract input"


def letta_run(*input_args, **input_kwargs):
    """Simple function that runs Letta agent"""
    try:
        client = Letta(base_url="http://localhost:8283")
        
        # Create memory blocks
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are talking to a user through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="You are a helpful AI assistant. Be friendly and concise.",
            ),
        ]

        # Create agent
        agent = client.agents.create(
            name=f"runagent-letta-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="You are a helpful AI assistant integrated with RunAgent. Respond naturally and helpfully.",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            include_base_tools=True
        )

        print(f"✅ Letta agent created with ID: {agent.id}")
        
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
    """Simple function that streams from Letta agent"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Create memory blocks
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are talking to a user through RunAgent framework",
            ),
            CreateBlock(
                label="persona",
                value="You are a helpful AI assistant. Be friendly and concise.",
            ),
        ]

        # Create agent
        agent = client.agents.create(
            name=f"runagent-letta-stream-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="You are a helpful AI assistant integrated with RunAgent. Respond naturally and helpfully.",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            include_base_tools=True
        )

        print(f"✅ Letta streaming agent created with ID: {agent.id}")
        
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