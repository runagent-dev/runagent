from runagent import RunAgentClient


client = RunAgentClient(
    agent_id="18aa1012-acc2-4416-9c7f-6242f874374a",
    entrypoint_tag="screenplay_generate",
    local=False
)


discussion = (
    "Two friends debate whether pineapple belongs on pizza while waiting at a coffee bar.\n"
    "They trade points back and forth without insults or stage directions."
)

result = client.run(
    discussion=discussion
)

print(result)


