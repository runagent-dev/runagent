from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="528bfbf3-433f-4728-a203-3310dad42dee",
    entrypoint_tag="simulate_stream",
    local=False
)

# Run and print ALL output including logs
for update in client.run(
    num_agents=5,
    total_days=2,
    sessions_per_day=2,
    model="gpt-4o-mini"
):
    # Print everything
    if update.get('type') == 'log':
        # Raw log output
        print(update['message'])
    else:
        # Structured events
        print(f"[{update['type']}] {update.get('message', '')}")