##non-streaming

# from runagent import RunAgentClient
# import asyncio


# ra_client = RunAgentClient(agent_id="7ada23ab-a092-447b-8471-b747eb1e5f9f", entrypoint_tag="generic", local=True)

# def main_with_complex_data():
#     # With complex inputs
#     agent_results = ra_client.run({
#         "query": "Fix my slow laptop",
#         "num_solutions": 3,
#         "constraints": [{"type": "budget", "value": 100, "priority": "high"}],
#         "user_context": {"experience_level": "beginner"},
#         "metadata": {"test": True}
#     })
    
#     print(agent_results)



# if __name__ == "__main__":
#     main_with_complex_data()



##streaming

from runagent import RunAgentClient
import asyncio


ra_client = RunAgentClient(agent_id="7ada23ab-a092-447b-8471-b747eb1e5f9f", entrypoint_tag="generic_stream", local=True)


def main_streaming():
    # Streaming version
    for chunk in ra_client.run({
        "query": "My fridge is not getting cold.",
        "num_solutions": 3,
        "constraints": [{"type": "budget", "value": 100, "priority": "high"}],
        "user_context": {"experience_level": "beginner"},
        "metadata": {"test": True}
    }):
        print(chunk)

if __name__ == "__main__":
    main_streaming()
