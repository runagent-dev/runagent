from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description="A report-writing assistant built with agno that generates structured reports from user inputs and provided data. It can create executive summaries, detailed sections, and recommendations based on the user's topic, scope, and source material.",
    instructions="Focus on: Generate structured, formatted reports from topic, scope, and source information.",
    markdown=True
)

def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    input_parts = []
    for field in ["title", "topic", "audience", "scope", "sources", "format_style", "length", "deadline", "include_summary", "include_recommendations"]:
        if input_kwargs.get(field):
            input_parts.append(f"{field}: {input_kwargs[field]}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {str(input_args[0])}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\n".join(input_parts)
    
    # Add context about the agent's purpose
    full_prompt = f"""
    A report-writing assistant built with agno that generates structured reports from user inputs and provided data. It can create executive summaries, detailed sections, and recommendations based on the user's topic, scope, and source material.
    
    User input:
    {user_input}
    
    Please provide a helpful response focused on: Generate structured, formatted reports from topic, scope, and source information.
    """
    
    response = agent.run(full_prompt)
    
    return {
        "content": response.content if hasattr(response, 'content') else str(response),
    }

def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    input_parts = []
    for field in ["title", "topic", "audience", "scope", "sources", "format_style", "length", "deadline", "include_summary", "include_recommendations"]:
        if input_kwargs.get(field):
            input_parts.append(f"{field}: {input_kwargs[field]}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {str(input_args[0])}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\n".join(input_parts)
    
    full_prompt = f"""
    A report-writing assistant built with agno that generates structured reports from user inputs and provided data. It can create executive summaries, detailed sections, and recommendations based on the user's topic, scope, and source material.
    
    User input:
    {user_input}
    
    Please provide a helpful response focused on: Generate structured, formatted reports from topic, scope, and source information.
    """
    
    for chunk in agent.run(full_prompt, stream=True):
        yield {
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }
