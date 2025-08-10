from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.agent.workflow import FunctionAgent

# Define a simple tool based on agent functionality
def process_request(query: str) -> str:
    """Process user request based on agent functionality."""
    return f"Processing: {query} for Provide personalized movie recommendations using RAG over a movie dataset/index"

# Create an agent workflow
agent = FunctionAgent(
    tools=[process_request],
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="A retrieval-augmented movie recommendation agent that uses LlamaIndex to combine user preferences with a movie knowledge base (plots, genres, cast, reviews) to produce personalized recommendations and explanations. It supports filtering, ranking, and returning relevant metadata and rationale for each suggestion. Focus on: Provide personalized movie recommendations using RAG over a movie dataset/index",
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    input_parts = []
    for field in ["user_query", "preferred_genres", "preferred_actors_directors", "release_year_range", "minimum_rating", "language", "max_results", "include_synopses", "explain_reasons"]:
        if input_kwargs.get(field):
            input_parts.append(f"{field}: {input_kwargs[field]}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {str(input_args[0])}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\n".join(input_parts)
    
    response = await agent.run(user_input)
    return response

async def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    input_parts = []
    for field in ["user_query", "preferred_genres", "preferred_actors_directors", "release_year_range", "minimum_rating", "language", "max_results", "include_synopses", "explain_reasons"]:
        if input_kwargs.get(field):
            input_parts.append(f"{field}: {input_kwargs[field]}")
    
    if not input_parts and input_args:
        input_parts.append(f"Input: {str(input_args[0])}")
    
    if not input_parts:
        input_parts.append("No specific input provided")
    
    user_input = "\n".join(input_parts)
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        if isinstance(event, AgentStream):
            yield event
        else:
            yield str(event)
