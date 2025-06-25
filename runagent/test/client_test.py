from runagent import RunAgentClient

ra = RunAgentClient(agent_id="330489a3-ff37-46f3-b88b-432bce5000da")
ra.run(
    input_args=[],
    input_kwargs={"query": "How to I fix my broken phone", "num_solutions": 2},
)
