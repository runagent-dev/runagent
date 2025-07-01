import asyncio
from runagent import AsyncRunAgentClient

async_ra = AsyncRunAgentClient(agent_id="d606beb5-a391-409d-9b5d-2adf86842292")


async def main():
    agent_results = await async_ra.run_generic({
        "query": "How to I fix my broken phone?",
        "num_solutions": 4,  # Keep between 1-5
        "solutions": [],
        "validated_results": "",
    })
    
    print(agent_results)

# Run the async function
asyncio.run(main())