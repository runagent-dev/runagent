import asyncio
from runagent import RunAgentClient

async_ra = RunAgentClient(agent_id="0a9d9502-4bfe-44ca-ba6f-01fc19ef0dce",entrypoint_tag="basic", local=True)


def main():
    agent_results = async_ra.run({
        "query": "How to I fix my broken phone?",
        "num_solutions": 4,  # Keep between 1-5
        "solutions": [],
        "validated_results": "",
    })
    
    print(agent_results)

if __name__ == "__main__":
    main()