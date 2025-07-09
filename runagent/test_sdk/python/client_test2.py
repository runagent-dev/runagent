from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="eb4de46a-cc77-4fa4-920b-5adfe2add968",
    local=True,
    entrypoint_tag="generic"
    )


agent_results = ra.run(
    sender_name="Alice Johnson",
    recipient_name="Mr. Daniel Smith",
    subject="Request for Meeting Next Week"
)

print(agent_results)

# ==================================

# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="eb4de46a-cc77-4fa4-920b-5adfe2add968",
#     entrypoint_tag="default_stream",
#     local=True
#     )

# for chunk in ra.run({
#         "query": "How to I fix my broken phone?",
#         "num_solutions": 4,  # Keep between 1-5
#         "solutions": [],
#         "validated_results": "",
# }):
#     print(chunk)
