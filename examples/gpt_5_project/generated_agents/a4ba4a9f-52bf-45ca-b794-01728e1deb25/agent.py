from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

# Initialize LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.3)

# Create the agent
agent = FunctionAgent(
    tools=[],  # Add tools as needed
    llm=llm,
    system_prompt="A math problem solving agent that uses LlamaIndex to retrieve relevant mathematical resources, worked examples, and formula references to generate step-by-step solutions. It supports multiple problem types (algebra, calculus, geometry) and can cite source documents or examples used in reasoning. Focus on: Retrieve relevant documents/examples with LlamaIndex and produce step-by-step solutions and citations for math problems."
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    user_input = ""
    for field in ['problem_text', 'problem_type', 'desired_detail_level', 'preferred_solution_format', 'reference_documents']:
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
    for field in ['problem_text', 'problem_type', 'desired_detail_level', 'preferred_solution_format', 'reference_documents']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        yield event
