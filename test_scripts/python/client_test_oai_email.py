# from pprint import pprint
# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="36b98063-2397-4f89-b7e9-cfe6e998e048",
#     entrypoint_tag="generic_email",
#     local=True
#     )


# agent_results = ra.run(
#     sender_name="Alice Johnson",
#     recipient_name="Mr. Daniel Smith",
#     subject="Request for Meeting Next Week"
# )

# print(agent_results)

# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="36b98063-2397-4f89-b7e9-cfe6e998e048",
    entrypoint_tag="email_stream",
    local=True
    )

for chunk in ra.run(
    sender_name="Alice Johnson",
    recipient_name="Mr. Daniel Smith",
    subject="Request for Meeting Next Week"
):
    print(chunk, end="")
