from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    description="A content writer agent that generates blog posts, articles, and marketing copy based on user-provided topics, tone, and length. It produces structured drafts with headings, introductions, conclusions, and optional SEO suggestions.",
    instructions="Focus on: Generate polished, topic-focused written content and provide basic SEO and formatting recommendations.",
    markdown=True
)

def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    prompt = ""
    for field in ['topic', 'audience', 'tone', 'word_count', 'keywords', 'content_type', 'call_to_action', 'additional_requirements']:
        if input_kwargs.get(field):
            prompt = str(input_kwargs[field])
            break
    
    if not prompt and input_args:
        prompt = str(input_args[0])
    
    if not prompt:
        prompt = "Hello, how can I help you?"
    
    # Add context about the agent's purpose
    full_prompt = f"""
    A content writer agent that generates blog posts, articles, and marketing copy based on user-provided topics, tone, and length. It produces structured drafts with headings, introductions, conclusions, and optional SEO suggestions.
    
    User request: {prompt}
    
    Please provide a helpful response focused on: Generate polished, topic-focused written content and provide basic SEO and formatting recommendations.
    """
    
    response = agent.run(full_prompt)
    
    return {
        "content": response.content if hasattr(response, 'content') else str(response),
    }

def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    prompt = ""
    for field in ['topic', 'audience', 'tone', 'word_count', 'keywords', 'content_type', 'call_to_action', 'additional_requirements']:
        if input_kwargs.get(field):
            prompt = str(input_kwargs[field])
            break
    
    if not prompt and input_args:
        prompt = str(input_args[0])
    
    full_prompt = f"""
    A content writer agent that generates blog posts, articles, and marketing copy based on user-provided topics, tone, and length. It produces structured drafts with headings, introductions, conclusions, and optional SEO suggestions.
    
    User request: {prompt}
    
    Please provide a helpful response focused on: Generate polished, topic-focused written content and provide basic SEO and formatting recommendations.
    """
    
    for chunk in agent.run(full_prompt, stream=True):
        yield {
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }

# Keep original functions for backward compatibility  
agent_run_stream = partial(agent.run, stream=True)
