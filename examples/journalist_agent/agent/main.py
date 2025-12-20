from agno.agent import Agent
from agno.team import Team
from agno.tools.serper import SerperTools
from agno.tools.newspaper4k import Newspaper4kTools
from textwrap import dedent

# Model string format: "provider:model_id"
model_string = "openai:gpt-4o-mini"

# Create journalist team
journalist_team = Team(
    model=model_string,
    members=[
        Agent(
            model=model_string,
            name="Researcher",
            role="Research Specialist",
            tools=[SerperTools()],
            instructions=dedent("""\
                You are a research specialist for the New York Times.
                - Generate 3-5 relevant search terms for any given topic
                - Use search_web to find authoritative, high-quality sources
                - Analyze results and identify the 10 most credible URLs
                - Prioritize official sources, academic papers, and reputable news outlets
            """),
        ),
        Agent(
            model=model_string,
            name="Writer",
            role="Senior Writer",
            tools=[Newspaper4kTools()],
            instructions=dedent("""\
                You are a senior writer for the New York Times.
                - Use get_article_text to read content from provided URLs
                - Write comprehensive articles with 15+ paragraphs
                - Include proper citations and balanced perspectives
                - Maintain NYT's high standards for clarity and engagement
                - Never plagiarize or fabricate information
            """),
        ),
    ],
    instructions=dedent("""\
        You are the Editor-in-Chief of a journalism team at the New York Times.
        Coordinate your team to produce high-quality articles:
        1. Direct the Researcher to find authoritative sources on the topic
        2. Have the Writer create a comprehensive article using those sources
        3. Review and refine the final article for accuracy, clarity, and engagement
        Ensure every article meets NYT's prestigious standards.
    """),
)


def create_article(topic: str):
    """
    Create a high-quality news article on a given topic
    
    Args:
        topic: The topic to write about
    """
    response = journalist_team.run(topic, stream=False)
    return {
        "article": response.content,
        "success": True
    }


def create_article_stream(topic: str):
    """Streaming version of article creation"""
    for chunk in journalist_team.run(topic, stream=True):
        yield {"content": chunk if hasattr(chunk, 'content') else str(chunk)}