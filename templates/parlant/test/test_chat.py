import asyncio
import time
from parlant.client import AsyncParlantClient
from datetime import datetime
import math


async def create_agent_with_tools(client: AsyncParlantClient):
    """Create an agent with calculator and time tools."""
    
    # Check if agent already exists
    agents = await client.agents.list()
    for agent in agents:
        if agent.name == "Calculator Assistant":
            print(f"✅ Found existing agent: {agent.name}")
            return agent.id
    
    # Create new agent
    agent = await client.agents.create(
        name="Calculator Assistant",
        description="A helpful assistant that can perform calculations and tell you the current time."
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
            "condition": "User greets or says hello",
            "action": "Respond with a warm greeting and explain what you can help with (calculations and current time)"
        },
        {
            "condition": "User asks what you can do or for help",
            "action": "Explain that you can perform mathematical calculations and provide the current time"
        }
    ]
    
    for guideline in guidelines:
        await client.agents.guidelines.create(
            agent_id=agent.id,
            **guideline
        )
    
    print(f"✅ Added {len(guidelines)} guidelines and 2 tools")
    return agent.id


async def chat_with_agent(message: str, agent_id: str, client: AsyncParlantClient) -> str:
    """Send a message to the agent and get response."""
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
            return response_data.get("data", {}).get("message", "No response")
        else:
            return "❌ No response from agent"
            
    except Exception as e:
        return f"❌ Error: {e}"


async def main():
    """Main function."""
    client = AsyncParlantClient(base_url="http://localhost:8800")
    
    try:
        # Wait for server to be ready
        print("🔄 Connecting to Parlant server...")
        await client.agents.list()  # Test connection
        print("✅ Connected to server!")
        
        # Create agent with tools
        agent_id = await create_agent_with_tools(client)
        
        # Test messages
        test_messages = [
            "Hey babe how can you help me?",
            "What time is it?", 
            "Calculate 25 * 4 + 10",
            "What's the square root of 144?"
        ]
        
        print("\n💬 Testing chat:")
        print("=" * 40)
        
        for message in test_messages:
            print(f"\n👤 You: {message}")
            response = await chat_with_agent(message, agent_id, client)
            print(f"🤖 Agent: {response}")
            await asyncio.sleep(1)
            
        print(f"\n🎉 Done! Your agent is running at http://localhost:8800")
        print(f"Agent ID: {agent_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure Parlant server is running: parlant-server run")


if __name__ == "__main__":
    asyncio.run(main())