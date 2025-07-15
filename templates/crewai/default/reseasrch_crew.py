from crewai import Agent, Task, Crew

researcher = Agent(
    role='Research Analyst',
    goal='Find accurate information about topics',
    backstory='You are an experienced researcher with a keen eye for detail.',
    verbose=True
)

research_task = Task(
    description='Research on : {topic}',
    agent=researcher,
    expected_output='A summary of 3-5 key benefits of renewable energy'
)

crew = Crew(
    agents=[researcher],
    tasks=[research_task],
    verbose=True
)


def run_stream(topic):
    result = crew.kickoff(
        inputs={
            'topic': topic
        })
    return result
