import asyncio
import parlant.sdk as p
from datetime import datetime
import math


@p.tool
async def get_current_time(context: p.ToolContext) -> p.ToolResult:
    """Get the current date and time."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return p.ToolResult(f"Current time: {current_time}")


@p.tool
async def calculator(context: p.ToolContext, expression: str) -> p.ToolResult:
    """Calculate mathematical expressions. Supports basic operations (+, -, *, /), powers (**), and math functions like sqrt, sin, cos, etc."""
    try:
        # Safe evaluation - only allow math operations
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
        })
        
        # Replace common math function names to make it more user-friendly
        expression = expression.replace("^", "**")  # Allow ^ for power
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return p.ToolResult(f"Result: {result}")
    
    except Exception as e:
        return p.ToolResult(f"Error calculating '{expression}': {str(e)}")


async def main():
    async with p.Server() as server:
        # Create the agent
        agent = await server.create_agent(
            name="Calculator Assistant",
            description="A helpful assistant that can perform calculations and tell you the current time."
        )
        
        # Create context variable for current time (automatically updated)
        await agent.create_variable(
            name="current-datetime", 
            tool=get_current_time
        )
        
        # Guidelines for agent behavior
        await agent.create_guideline(
            condition="User asks for the current time or date",
            action="Get the current time and provide it in a friendly manner",
            tools=[get_current_time]
        )
        
        await agent.create_guideline(
            condition="User asks to calculate something or provides a math expression",
            action="Use the calculator tool to solve the mathematical expression and explain the result",
            tools=[calculator]
        )
        
        await agent.create_guideline(
            condition="User greets or says hello",
            action="Respond with a warm greeting and explain what you can help with (calculations and current time)"
        )
        
        await agent.create_guideline(
            condition="User asks what you can do or for help",
            action="Explain that you can perform mathematical calculations and provide the current time"
        )
        
        await agent.create_guideline(
            condition="User says goodbye or thanks",
            action="Respond politely and invite them to ask if they need more help"
        )
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down Calculator Assistant...")


if __name__ == "__main__":
    asyncio.run(main())