from runagent import RunAgentClient

ra = RunAgentClient(agent_id="055b73d7-6239-4a94-a156-1193fcf33ff0")
# agent_results = ra.run_generic(query="How to I fix my broken phone", num_solutions=2)
# print(agent_results)

agent_results = ra.run_generic({
    "query": "How to I fix my broken phone?",
    "num_solutions": 4,  # Keep between 1-5
    "solutions": [],
    "validated_results": "",
})

print(agent_results)