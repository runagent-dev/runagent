from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o"
    ),
    markdown=True
)

# Original functions (keeping for backward compatibility)
agent_run_stream = partial(agent.run, stream=True)

def agent_print_response(prompt: str):
    """Non-streaming response that returns serializable content"""
    # Get the response object
    response = agent.run(prompt)
    
    # Return structured data that can be serialized
    return {
        "content": response.content if hasattr(response, 'content') else str(response),
    }

def agent_print_response_stream(prompt: str):
    """Streaming response that yields serializable chunks"""
    # Use the regular streaming but with additional metadata
    for chunk in agent.run(prompt, stream=True):
        yield {
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }