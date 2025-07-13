from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(
        id="gpt-4o"
    ),
    markdown=True
)

agent_run_stream = partial(agent.run, stream=True)
