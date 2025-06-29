import asyncio
from runagent import AsyncRunAgentClient

async_ra = AsyncRunAgentClient(agent_id="055b73d7-6239-4a94-a156-1193fcf33ff0")


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