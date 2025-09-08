import asyncio
import parlant.sdk as p
from typing import Dict, Any, AsyncGenerator
import uuid
import time

# Global agent instance for reuse across entrypoints
_parlant_agent = None
_parlant_server = None


@p.tool
async def get_current_time(context: p.ToolContext) -> p.ToolResult:
    """Get the current time."""
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return p.ToolResult(f"Current time: {current_time}")


@p.tool
async def weather_info(context: p.ToolContext, city: str) -> p.ToolResult:
    """Get weather information for a city (mock implementation)."""
    # Mock weather data
    weather_data = {
        "paris": "Partly cloudy, 18°C",
        "london": "Rainy, 12°C", 
        "new york": "Sunny, 22°C",
        "tokyo": "Cloudy, 16°C"
    }
    
    city_lower = city.lower()
    weather = weather_data.get(city_lower, f"Weather data not available for {city}")
    return p.ToolResult(f"Weather in {city}: {weather}")


async def get_parlant_agent():
    """Get or create the Parlant agent instance."""
    global _parlant_agent, _parlant_server
    
    if _parlant_agent is None:
        # Create the Parlant server and agent
        _parlant_server = p.Server()
        await _parlant_server.__aenter__()
        
        # Create the agent
        _parlant_agent = await _parlant_server.create_agent(
            name="Assistant",
            description="""A helpful AI assistant that can provide information, 
            answer questions, and help with various tasks. I am professional, 
            friendly, and always try to be helpful."""
        )
        
        # Create context variable for current time
        await _parlant_agent.create_variable(
            name="current-datetime", 
            tool=get_current_time
        )
        
        # Add guidelines for behavior control
        await _parlant_agent.create_guideline(
            condition="User asks about weather",
            action="Get weather information and provide a helpful response with suggestions",
            tools=[weather_info]
        )
        
        await _parlant_agent.create_guideline(
            condition="User asks about time or current time",
            action="Provide the current time in a friendly manner",
            tools=[get_current_time]
        )
        
        await _parlant_agent.create_guideline(
            condition="User greets or says hello",
            action="Respond with a warm, professional greeting and ask how you can help"
        )
        
        await _parlant_agent.create_guideline(
            condition="User asks for help or doesn't know what to ask",
            action="Provide helpful suggestions of things you can assist with, including weather, time, general questions"
        )
        
        await _parlant_agent.create_guideline(
            condition="User says goodbye or thanks",
            action="Respond politely and invite them to ask if they need anything else"
        )
    
    return _parlant_agent


async def simple_chat(message: str) -> Dict[str, Any]:
    """
    Simple chat function that actually processes the message through Parlant's conversation engine.
    """
    try:
        # Ensure agent is available
        agent = await get_parlant_agent()
        

        try:
            # Create a mock customer and session context
            customer = await _parlant_server.create_customer(name="User")
            
            # Try to process the message through Parlant's engine
            # This should trigger guidelines and tools automatically
            response = await agent.process_conversation_turn(
                customer_id=customer.id,
                message=message
            )
            
            return {
                "content": response.message if hasattr(response, 'message') else str(response),
                "type": "parlant_conversation_response",
                "agent_name": agent.name,
                "message_received": message,
                "guidelines_applied": getattr(response, 'guidelines_applied', []),
                "tools_used": getattr(response, 'tools_used', [])
            }
            
        except AttributeError:
            # Method 2: Try alternative conversation processing
            try:
                conversation_result = await _parlant_server.handle_customer_message(
                    agent=agent,
                    customer_message=message
                )
                
                return {
                    "content": str(conversation_result),
                    "type": "parlant_response"
                }
            except AttributeError:
                # Method 3: Direct tool execution based on message content
                # return await _process_message_with_guidelines(agent, message)
                return "error found"
        
    except Exception as e:
        return {
            "content": f"Error processing message: {str(e)}",
            "type": "error",
            "error": str(e),
            "agent_name": getattr(agent, 'name', 'Unknown') if 'agent' in locals() else 'Unknown'
        }





async def chat_stream(message: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streaming chat function - simplified approach.
    """
    try:
        agent = await get_parlant_agent()
        
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
                "content": word + " ",
                "type": "parlant_stream",
                "chunk_type": "text",
                "agent_name": agent.name,
                "is_final": i == len(words) - 1
            }
            await asyncio.sleep(0.1)  # Simulate streaming delay
                
    except Exception as e:
        yield {
            "content": f"Error in streaming chat: {str(e)}",
            "type": "error",
            "error": str(e),
            "agent_name": getattr(agent, 'name', 'Unknown') if 'agent' in locals() else 'Unknown'
        }


async def agent_with_guidelines(message: str, guidelines: list = None) -> Dict[str, Any]:
    """
    Create a temporary agent with custom guidelines.
    """
    try:
        # Create a temporary server and agent
        temp_server = p.Server()
        await temp_server.__aenter__()
        
        temp_agent = await temp_server.create_agent(
            name="CustomAssistant",
            description="A customizable assistant with user-defined guidelines"
        )
        
        # Add custom guidelines if provided
        if guidelines:
            for guideline in guidelines:
                await temp_agent.create_guideline(
                    condition=guideline.get('condition', 'Always'),
                    action=guideline.get('action', 'Respond helpfully'),
                    tools=guideline.get('tools', [])
                )
        
        # For now, return a response showing the agent was created with guidelines
        response_content = f"Custom agent '{temp_agent.name}' created with {len(guidelines) if guidelines else 0} custom guidelines. Message received: {message}"
        
        # Clean up
        await temp_server.__aexit__(None, None, None)
        
        return {
            "content": response_content,
            "type": "parlant_custom",
            "guidelines_count": len(guidelines) if guidelines else 0,
            "custom_guidelines": guidelines,
            "agent_name": temp_agent.name
        }
        
    except Exception as e:
        return {
            "content": f"Error with custom guidelines: {str(e)}",
            "type": "error",
            "error": str(e)
        }


