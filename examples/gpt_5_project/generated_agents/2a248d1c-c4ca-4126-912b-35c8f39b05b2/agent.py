from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

# Initialize LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.3)

# Create the agent
agent = FunctionAgent(
    tools=[],  # Add tools as needed
    llm=llm,
    system_prompt="An AI agent that solves math problems by retrieving relevant documents and worked examples from a knowledge base using LlamaIndex, then applying symbolic/math reasoning to produce step-by-step solutions. It supports numeric computations, algebraic manipulations, and explanations with citations to source documents. Focus on: Retrieve math-related documents/examples and generate step-by-step solutions and explanations for user-provided math problems."
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    user_input = ""
    for field in ['problem_statement', 'preferred_solution_format', 'allowed_tools', 'reference_documents (optional)', 'precision_or_rounding (optional)']:
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
    for field in ['problem_statement', 'preferred_solution_format', 'allowed_tools', 'reference_documents (optional)', 'precision_or_rounding (optional)']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        yield event
