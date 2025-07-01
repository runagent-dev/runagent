from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="694624f8-5e66-4f23-b0b7-28d00d75931c",
    local=True
    )


agent_results = ra.run_generic({
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    })

print(agent_results)