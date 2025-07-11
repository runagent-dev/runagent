from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="89883120-8a12-4464-80a7-5a52852bab33",
    local=True
    )


for out in ra.run_generic_stream(
    sender_name="Alice Johnson",
    recipient_name="Mr. Daniel Smith",
    subject="Request for Meeting Next Week"
):
    print("=====??")
    print(out)
    print("??====")