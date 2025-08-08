from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

# Initialize LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.3)

# Create the agent
agent = FunctionAgent(
    tools=[],  # Add tools as needed
    llm=llm,
    system_prompt="A math solver that uses LlamaIndex to retrieve relevant math explanations, worked examples, and reference notes from a curated document store, then composes step-by-step solutions for user-provided problems. It can handle algebra, calculus, and basic applied math by combining retrieved knowledge with on-the-fly symbolic reasoning. Focus on: Retrieve relevant math content from indexed documents and generate clear, step-by-step solutions to user-submitted math problems."
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    user_input = ""
    for field in ['math_problem_text', 'preferred_solution_style', 'desired_detail_level', 'reference_documents_ids', 'output_format']:
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
    for field in ['math_problem_text', 'preferred_solution_style', 'desired_detail_level', 'reference_documents_ids', 'output_format']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        yield event
