import asyncio
from runagent import AsyncRunAgentClient

async def main():
    ra = AsyncRunAgentClient(agent_id="055b73d7-6239-4a94-a156-1193fcf33ff0")
    # agent_results = await ra.run_generic(query="How to I fix my broken phone", num_solutions=2)
    # print(agent_results)

    async for out in ra.run_generic_stream({
        "query": "How to I fix my broken phone?",
        "num_solutions": 4
    }):
        print("=====??")
        print(out)
        print("??====")

# Run the async function
asyncio.run(main())