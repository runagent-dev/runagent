import asyncio
from parlant.client import AsyncParlantClient
from typing import Dict, Any, AsyncGenerator
import time

# Global client and agent_id for reuse
_parlant_client = None
_agent_id = None


async def get_parlant_client():
    """Get or create the Parlant client instance."""
    global _parlant_client
    
    if _parlant_client is None:
        _parlant_client = AsyncParlantClient(base_url="http://localhost:8800")
        
        # Test connection
        try:
            await _parlant_client.agents.list()
        except Exception as e:
            raise Exception(f"Failed to connect to Parlant server at http://localhost:8800. Make sure it's running. Error: {e}")
    
    return _parlant_client


async def create_agent_with_tools(client: AsyncParlantClient):
    """Create an agent with calculator and time tools."""
    
    # Check if agent already exists
    agents = await client.agents.list()
    for agent in agents:
        if agent.name == "RunAgent Assistant":
            print(f"✅ Found existing agent: {agent.name}")
            return agent.id
    
    # Create new agent
    agent = await client.agents.create(
        name="RunAgent Assistant",
        description="A helpful assistant that can provide information, answer questions, help with calculations and tell you the current time."
    )
    
    print(f"✅ Created new agent: {agent.name}")
    
    # Add calculator tool
    await client.agents.tools.create(
        agent_id=agent.id,
        name="calculator",
        description="Calculate mathematical expressions. Supports +, -, *, /, **, sqrt(), sin(), cos(), etc.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to calculate"
                }
            },
            "required": ["expression"]
        },
        implementation="""
try:
    import math
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow})
    
    expression = expression.replace("^", "**")
    result = eval(expression, {"__builtins__": {}}, allowed_names)
    return f"Result: {result}"
except Exception as e:
    return f"Error calculating '{expression}': {str(e)}"
"""
    )
    
    # Add time tool
    await client.agents.tools.create(
        agent_id=agent.id,
        name="get_current_time",
        description="Get the current date and time",
        parameters={"type": "object", "properties": {}, "required": []},
        implementation="""
from datetime import datetime
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
return f"Current time: {current_time}"
"""
    )
    
    # Add weather tool (mock implementation)
    await client.agents.tools.create(
        agent_id=agent.id,
        name="weather_info",
        description="Get weather information for a city",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city to get weather for"
                }
            },
            "required": ["city"]
        },
        implementation="""
# Mock weather data
weather_data = {
    "paris": "Partly cloudy, 18°C",
    "london": "Rainy, 12°C", 
    "new york": "Sunny, 22°C",
    "tokyo": "Cloudy, 16°C",
    "berlin": "Overcast, 15°C",
    "sydney": "Clear, 25°C"
}

city_lower = city.lower()
weather = weather_data.get(city_lower, f"Weather data not available for {city}")
return f"Weather in {city}: {weather}"
"""
    )
    
    # Add guidelines
    guidelines = [
        {
            "condition": "User asks for the current time or date",
            "action": "Get the current time and provide it in a friendly manner",
            "tools": ["get_current_time"]
        },
        {
            "condition": "User asks to calculate something or provides a math expression",
            "action": "Use the calculator tool to solve the mathematical expression and explain the result",
            "tools": ["calculator"]
        },
        {
            "condition": "User asks about weather",
            "action": "Get weather information using the weather_info tool and provide a helpful response",
            "tools": ["weather_info"]
        },
        {
            "condition": "User greets or says hello",
            "action": "Respond with a warm greeting and explain what you can help with (calculations, current time, weather, and general questions)"
        },
        {
            "condition": "User asks what you can do or for help",
            "action": "Explain that you can perform mathematical calculations, provide the current time, check weather information, and answer general questions"
        },
        {
            "condition": "User says goodbye or thanks",
            "action": "Respond politely and invite them to ask if they need anything else"
        }
    ]
    
    for guideline in guidelines:
        await client.agents.guidelines.create(
            agent_id=agent.id,
            **guideline
        )
    
    print(f"✅ Added {len(guidelines)} guidelines and 3 tools")
    return agent.id


async def get_or_create_agent():
    """Get or create the agent with full tools and guidelines setup."""
    global _agent_id
    
    if _agent_id is not None:
        return _agent_id
    
    client = await get_parlant_client()
    
    # Create agent with tools and guidelines
    _agent_id = await create_agent_with_tools(client)
    return _agent_id


async def chat_with_agent(message: str, agent_id: str) -> str:
    """Send a message to the agent and get response."""
    client = await get_parlant_client()
    
    try:
        # Create a chat session
        session = await client.sessions.create(
            agent_id=agent_id,
            allow_greeting=False
        )
        
        # Send message
        event = await client.sessions.create_event(
            session_id=session.id,
            kind="message",
            source="customer",
            message=message,
        )
        
        # Get response
        agent_messages = await client.sessions.list_events(
            session_id=session.id,
            min_offset=event.offset,
            source="ai_agent",
            kinds="message",
            wait_for_data=30,
        )
        
        if agent_messages:
            response_data = agent_messages[0].model_dump()
            return response_data.get("data", {}).get("message", "No response received")
        else:
            return "No response from agent"
            
    except Exception as e:
        return f"Error processing message: {str(e)}"


async def simple_chat(message: str) -> Dict[str, Any]:
    """
    Simple chat function that processes the message through Parlant's conversation engine.
    
    Args:
        message: The user's message
        
    Returns:
        Dict containing the response and metadata
    """
    try:
        # Ensure agent is available with full setup
        agent_id = await get_or_create_agent()
        
        # Get response from agent
        response = await chat_with_agent(message, agent_id)
        
        return {
            "content": response,
            "type": "parlant_conversation_response", 
            "agent_id": agent_id,
            "message_received": message,
            "timestamp": time.time(),
            "framework": "parlant",
            "entrypoint": "simple_chat"
        }
        
    except Exception as e:
        return {
            "content": f"Error processing message: {str(e)}",
            "type": "error",
            "error": str(e),
            "message_received": message,
            "framework": "parlant"
        }


async def chat_stream(message: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streaming chat function that simulates streaming responses.
    
    Args:
        message: The user's message
        
    Yields:
        Dict containing streaming response chunks
    """
    try:
        # Get the response first
        response = await simple_chat(message)
        
        if response["type"] == "error":
            yield response
            return
        
        # Simulate streaming by breaking up the response
        content = response["content"]
        words = content.split()
        
        for i, word in enumerate(words):
            yield {
                "content": word + " "
            }
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.05)
        
        # Final chunk to indicate completion
        yield {
            "content": "",
            "type": "parlant_stream",
            "chunk_type": "completion",
            "agent_id": response.get("agent_id"),
            "is_final": True,
            "message": "Stream completed",
            "framework": "parlant"
        }
                
    except Exception as e:
        yield {
            "content": f"Error in streaming chat: {str(e)}",
            "type": "error",
            "error": str(e),
            "message_received": message,
            "framework": "parlant"
        }