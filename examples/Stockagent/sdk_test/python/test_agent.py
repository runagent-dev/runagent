from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="6cf5351f-b228-4648-9a07-20608ef490be",
    entrypoint_tag="simulate_stream",
    local=False
)

# Run and print ALL output including logs
for update in client.run(
    num_agents="5",        
    total_days="2",        
    sessions_per_day="2",  
    model="gpt-4o-mini"
):
    print(update)
