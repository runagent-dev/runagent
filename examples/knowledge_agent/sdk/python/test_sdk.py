from runagent import RunAgentClient


client = RunAgentClient(
    agent_id="f426c8d7-0fb4-4c73-a1cd-4a102613c962",
    entrypoint_tag="kb_query_stream",
    local=False
)


# result = client.run(
#     prompt="List down the ingredients to make Massaman Gai"
# )
# print(result)
for chunk in client.run_stream(
    prompt="List down the ingredients to make Massaman Gai"
):
    print(chunk)



