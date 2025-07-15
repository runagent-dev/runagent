from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.agent.workflow import FunctionAgent


# Define a simple calculator tool
def multiply(a: float, b: float) -> float:
    """Useful for multiplying two numbers."""
    return a * b


# Create an agent workflow with our calculator tool
agent = FunctionAgent(
    tools=[multiply],
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="You are a helpful assistant that can multiply two numbers.",
)


async def do_multiply(math_query):
    return await agent.run(math_query)


async def stream_multiply(math_query):
    handler = agent.run(user_msg=math_query)
    async for event in handler.stream_events():
        if isinstance(event, AgentStream):
            yield event
