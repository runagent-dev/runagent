from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="7fa7f94f-f424-40fe-92f8-4b1f9da57c17",
    local=True
    )


agent_results = ra.run_generic({
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    })

print(agent_results)