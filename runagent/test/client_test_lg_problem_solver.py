from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="eb4de46a-cc77-4fa4-920b-5adfe2add968",
    entrypoint_tag="generic",
    local=True
    )

solution_result = ra.run({
        "query": "How to I fix my broken phone?",
        "num_solutions": 4
    })

print(solution_result)

# ==================================
from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="eb4de46a-cc77-4fa4-920b-5adfe2add968",
    entrypoint_tag="generic_stream",
    local=True
    )

for out in ra.run({
        "query": "How to I fix my broken phone?",
        "num_solutions": 4
}):
    print("=====??")
    print(out)
    print("??====")

