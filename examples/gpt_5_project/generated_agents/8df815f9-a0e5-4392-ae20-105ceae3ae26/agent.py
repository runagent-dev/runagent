from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent

# Initialize LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.3)

# Define calculation tools
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b

def subtract_numbers(a: float, b: float) -> float:
    """Subtract second number from first number."""
    return a - b

def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b

def divide_numbers(a: float, b: float) -> float:
    """Divide first number by second number."""
    if b == 0:
        return "Error: Cannot divide by zero"
    return a / b

# Create the agent with tools
agent = FunctionAgent(
    tools=[add_numbers, subtract_numbers, multiply_numbers, divide_numbers],
    llm=llm,
    system_prompt="A math solver that uses LlamaIndex to parse problems, retrieve relevant knowledge or worked examples from a document corpus, and generate step-by-step solutions. It can handle algebra, calculus, and numeric problem solving while citing sources and applying retrieved examples to improve solution accuracy. Focus on: Parse math problems, retrieve relevant documents or examples via LlamaIndex, and produce step-by-step solutions with citations.. Use the available mathematical tools to solve problems accurately."
)

async def agent_run(*input_args, **input_kwargs):
    """Main agent function"""
    
    # Extract input from various sources
    user_input = ""
    for field in ['problem_text', 'desired_solution_format', 'supporting_documents (optional)', 'precision_or_tolerance (optional)', 'show_steps (boolean)']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    if not user_input:
        user_input = "Hello, how can I help you with math?"
    
    response = await agent.run(user_input)
    return response

async def agent_run_stream(*input_args, **input_kwargs):
    """Streaming agent function"""
    
    user_input = ""
    for field in ['problem_text', 'desired_solution_format', 'supporting_documents (optional)', 'precision_or_tolerance (optional)', 'show_steps (boolean)']:
        if input_kwargs.get(field):
            user_input = str(input_kwargs[field])
            break
    
    if not user_input and input_args:
        user_input = str(input_args[0])
    
    handler = agent.run(user_msg=user_input)
    async for event in handler.stream_events():
        yield event
