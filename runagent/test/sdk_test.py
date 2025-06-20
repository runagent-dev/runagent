from runagent import RunAgent
sdk = RunAgent()

# print(sdk.list_templates())
# print(sdk.get_template_info("langchain", "basic"))
# sdk.init_project(folder="sdk-agent", framework="langchain")

# sdk.deploy_local(folder="/home/riamdriad5/runagent/runagent/sdk-agent")

# print(sdk.list_local_agents())



print(sdk.run_agent(agent_id="d6594457", message="meow", local=True))



# # Local Deployment
# sdk.deploy_local(folder="agent")
# sdk.list_local_agents()
# sdk.get_local_capacity()
# sdk.run_local_agent(agent_id="123", input_data={})
# sdk.start_local_server(port=8450)

# # Remote Deployment
# sdk.deploy_remote(folder="agent")
# sdk.upload_agent(folder="agent")
# sdk.start_remote_agent(agent_id="123")

# # Agent Management
# sdk.get_agent_info(agent_id="123", local=True)
# sdk.validate_agent(folder="agent")
# sdk.detect_framework(folder="agent")
# sdk.run_agent(agent_id="123", message="Hello")

# # Utilities
# sdk.cleanup_local_database(days_old=30)
# sdk.get_local_stats()