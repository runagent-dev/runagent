from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o-mini"
    ),
    markdown=True
)

# Original functions (keeping for backward compatibility)
agent_run_stream = partial(agent.run, stream=True)

def agent_print_response(prompt: str):
    """Non-streaming response that returns serializable content"""
    # Get the response object
    response = agent.run(prompt)
    
    # Extract the actual content from the response object
    # The response object has a .content attribute or .messages attribute
    if hasattr(response, 'content'):
        return response.content
    elif hasattr(response, 'messages') and response.messages:
        # Get the last message content
        return response.messages[-1].content if hasattr(response.messages[-1], 'content') else str(response.messages[-1])
    elif hasattr(response, 'text'):
        return response.text
    else:
        # Fallback: convert to string
        return str(response)

def agent_print_response_stream(prompt: str):
    """Streaming response that yields serializable chunks"""
    # Use the regular streaming but with additional metadata
    for chunk in agent.run(prompt, stream=True):
        yield {
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }