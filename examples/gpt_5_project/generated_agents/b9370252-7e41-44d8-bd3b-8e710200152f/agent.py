from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

# Initialize LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.3)

# Create the agent
agent = FunctionAgent(
    tools=[],  # Add tools as needed
    llm=llm,
    system_prompt="A math solver agent built on LlamaIndex that performs symbolic and numeric problem solving, shows step-by-step solutions, and retrieves relevant math references from indexed documents. It supports parsing problem statements, executing computations, and returning clear, verifiable derivations and final answers. Focus on: Parse math problems, perform symbolic and numeric computations, generate step-by-step solutions, and augment solving with retrieved math resources from a document index."
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    user_input = ""
    for field in ['problem_statement', 'preferred_solution_format', 'precision_or_tolerance', 'show_steps', 'context_documents']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    if not user_input:
        user_input = "Hello, how can I help you?"
    
    response = await agent.run(user_input)
    return response

async def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    user_input = ""
    for field in ['problem_statement', 'preferred_solution_format', 'precision_or_tolerance', 'show_steps', 'context_documents']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        yield event
