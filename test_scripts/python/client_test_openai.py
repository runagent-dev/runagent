# from pprint import pprint
# from runagent import RunAgentClient

# ra = RunAgentClient(
#     agent_id="40ca8515-a19a-49b2-8ef4-030f83bfc074",
#     entrypoint_tag="simple_assistant_extracted",  # "simple_assistant",  # 
#     local=True
#     )


# agent_results = ra.run(
#     user_msg="Analyze the benefits of remote work for software teams"
# )

# pprint(agent_results)

# ==================================

from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="40ca8515-a19a-49b2-8ef4-030f83bfc074",
    entrypoint_tag="simple_assistant_extracted_stream",
    local=True
    )

for chunk in ra.run(
    user_msg="Analyze the benefits of remote work for software teams"
):
    print(chunk)
